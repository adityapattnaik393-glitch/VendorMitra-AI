import os
import requests
from dotenv import load_dotenv

load_dotenv()

IBM_API_KEY = os.getenv("IBM_API_KEY")
IBM_PROJECT_ID = os.getenv("IBM_PROJECT_ID")
IBM_REGION = os.getenv("IBM_REGION", "us-south")

WATSONX_URL = f"https://{IBM_REGION}.ml.cloud.ibm.com"
GRANITE_MODEL_ID = "ibm/granite-3-8b-instruct"

_iam_token_cache = {"token": None}


def _get_iam_token() -> str:
    """Exchange IBM API key for a short-lived IAM bearer token."""
    if _iam_token_cache["token"]:
        return _iam_token_cache["token"]

    response = requests.post(
        "https://iam.cloud.ibm.com/identity/token",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
            "apikey": IBM_API_KEY,
        },
        timeout=30,
    )
    response.raise_for_status()
    token = response.json()["access_token"]
    _iam_token_cache["token"] = token
    return token


def generate_answer(question: str, context: str) -> str:
    """
    Call IBM Granite via watsonx.ai /text/generation endpoint.

    The prompt instructs Granite to act as VendorMitra, an assistant
    that helps Indian street vendors become digitally visible.
    """
    token = _get_iam_token()

    prompt = f"""You are VendorMitra, an AI assistant that helps Indian street
vendors and micro-entrepreneurs grow digitally. You provide practical
advice on UPI setup, MSME schemes, digital onboarding, local SEO,
QR codes, and government policies — grounded only in the context below.
Answer in the same language the vendor uses. Be concise and actionable.

Context:
{context}

Vendor question: {question}

Answer:"""

    payload = {
        "model_id": GRANITE_MODEL_ID,
        "project_id": IBM_PROJECT_ID,
        "input": prompt,
        "parameters": {
            "decoding_method": "greedy",
            "max_new_tokens": 512,
            "min_new_tokens": 10,
            "stop_sequences": [],
            "repetition_penalty": 1.1,
        },
    }

    response = requests.post(
        f"{WATSONX_URL}/ml/v1/text/generation?version=2023-05-29",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        json=payload,
        timeout=60,
    )

    # If the token expired (401), clear cache and retry once
    if response.status_code == 401:
        _iam_token_cache["token"] = None
        token = _get_iam_token()
        response = requests.post(
            f"{WATSONX_URL}/ml/v1/text/generation?version=2023-05-29",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            json=payload,
            timeout=60,
        )

    response.raise_for_status()

    data = response.json()
    results = data.get("results", [])
    if results:
        return results[0].get("generated_text", "").strip()

    return "I was unable to generate an answer at this time."
