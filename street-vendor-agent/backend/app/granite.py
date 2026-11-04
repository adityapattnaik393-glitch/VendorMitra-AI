"""IBM Granite client for watsonx.ai chat completions."""
import os
import time

import requests
from dotenv import load_dotenv

load_dotenv()

IBM_API_KEY = (os.getenv("IBM_API_KEY") or "").strip()
IBM_PROJECT_ID = (os.getenv("IBM_PROJECT_ID") or "").strip()
IBM_REGION = (os.getenv("IBM_REGION") or "us-south").strip()
IBM_MODEL_ID = (os.getenv("IBM_MODEL_ID") or "ibm/granite-4-h-small").strip()

WATSONX_URL = f"https://{IBM_REGION}.ml.cloud.ibm.com"
CHAT_URL = f"{WATSONX_URL}/ml/v1/text/chat?version=2024-10-08"
IAM_URL = "https://iam.cloud.ibm.com/identity/token"

_PLACEHOLDERS = {"", "your_ibm_api_key_here", "your_watsonx_project_id_here"}
_token_cache = {"token": None, "expires_at": 0.0}


class GraniteError(Exception):
    """Raised when IBM authentication or Granite inference fails."""


def config_problems() -> list[str]:
    problems = []
    if IBM_API_KEY in _PLACEHOLDERS:
        problems.append("IBM_API_KEY is missing or still a placeholder in backend/.env")
    if IBM_PROJECT_ID in _PLACEHOLDERS:
        problems.append("IBM_PROJECT_ID is missing or still a placeholder in backend/.env")
    return problems


def _ibm_error_text(response: requests.Response) -> str:
    try:
        body = response.json()
        errors = body.get("errors") or []
        if errors:
            first = errors[0]
            return f"{first.get('code', '')}: {first.get('message', '')}".strip(": ")
        return body.get("errorMessage") or body.get("message") or response.text[:300]
    except ValueError:
        return response.text[:300]


def get_iam_token(force_refresh: bool = False) -> str:
    """Exchange the API key for a bearer token, cached until shortly before expiry."""
    problems = config_problems()
    if problems:
        raise GraniteError("; ".join(problems))

    if (
        not force_refresh
        and _token_cache["token"]
        and time.time() < _token_cache["expires_at"]
    ):
        return _token_cache["token"]

    try:
        response = requests.post(
            IAM_URL,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
                "apikey": IBM_API_KEY,
            },
            timeout=30,
        )
    except requests.RequestException as error:
        raise GraniteError(f"Cannot reach IBM IAM (check internet/proxy): {error}") from error

    if response.status_code != 200:
        raise GraniteError(
            f"IBM IAM rejected the API key (HTTP {response.status_code}): "
            f"{_ibm_error_text(response)}"
        )

    data = response.json()
    _token_cache["token"] = data["access_token"]
    _token_cache["expires_at"] = time.time() + int(data.get("expires_in", 3600)) - 60
    return _token_cache["token"]


def list_available_chat_models() -> list[str]:
    """List available Granite chat models in the configured watsonx region."""
    try:
        response = requests.get(
            f"{WATSONX_URL}/ml/v1/foundation_model_specs",
            params={"version": "2024-09-16", "limit": 200},
            timeout=30,
        )
        response.raise_for_status()
    except requests.RequestException as error:
        raise GraniteError(f"Could not list models in {IBM_REGION}: {error}") from error

    models = []
    for spec in response.json().get("resources", []):
        model_id = spec.get("model_id", "")
        if "granite" not in model_id.lower():
            continue
        functions = {item.get("id") for item in spec.get("functions", [])}
        states = {item.get("id") for item in spec.get("lifecycle", [])}
        if "text_chat" in functions and not {"withdrawn", "deprecated"} & states:
            models.append(model_id)
    return sorted(models)


def generate_answer(
    question: str,
    context: str,
    task: str = "general",
    vendor_context: str = "",
    max_tokens: int = 700,
    preferred_language: str = "English",
) -> str:
    """Call IBM Granite on watsonx.ai and return the answer text."""
    task_guidance = {
        "business_profile": "Draft an accurate short business profile using only supplied vendor details.",
        "upi_setup": "Give practical UPI and QR-code onboarding steps supported by the sources.",
        "local_seo": "Suggest local listing and discoverability actions based on the stated location.",
        "customer_engagement": "Suggest practical customer communication and repeat-visit ideas.",
        "general": "Answer the vendor's question directly and offer relevant digitalization steps.",
    }.get(task, "Answer the vendor's question directly.")
    vendor_section = f"\nVendor profile:\n{vendor_context}\n" if vendor_context else ""

    system = (
        "You are VendorMitra, an AI assistant that helps Indian street vendors and "
        "micro-entrepreneurs grow digitally. Provide concise, practical guidance.\n"
        f"Task: {task}. {task_guidance}\n"
        "Use the retrieved context as the only source for government policies, scheme "
        "eligibility, fees, dates and other factual claims. Do not claim real-time access "
        "to government portals, fintech apps, commerce platforms or consumer data. Do not "
        "invent local demand, pricing, geolocation or business details. If the sources do "
        "not support a current or location-specific claim, say so and suggest confirming "
        "it with the relevant official source. "
        f"Write the entire answer in {preferred_language}. For Hindi, use natural Hindi "
        "in Devanagari script, even when the question is written in English. Do not "
        "switch languages unless the vendor asks you to. Be concise and actionable."
    )
    user = f"{vendor_section}\nRetrieved context:\n{context}\n\nVendor question: {question}"
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    payload = {
        "model_id": IBM_MODEL_ID,
        "project_id": IBM_PROJECT_ID,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0,
    }

    token = get_iam_token()
    try:
        response = requests.post(
            CHAT_URL,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            json=payload,
            timeout=90,
        )
        if response.status_code == 401:
            token = get_iam_token(force_refresh=True)
            response = requests.post(
                CHAT_URL,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                json=payload,
                timeout=90,
            )
    except requests.RequestException as error:
        raise GraniteError(f"Cannot reach watsonx.ai at {WATSONX_URL}: {error}") from error

    if response.status_code != 200:
        raise GraniteError(
            f"watsonx.ai returned HTTP {response.status_code} for model "
            f"'{IBM_MODEL_ID}' in region '{IBM_REGION}': {_ibm_error_text(response)}. "
            "Run `python -m app.check_granite` to see which models your region serves."
        )

    choices = response.json().get("choices") or []
    if choices:
        answer = (choices[0].get("message", {}).get("content") or "").strip()
        if answer:
            return answer
    raise GraniteError("watsonx.ai returned an empty answer.")


def test_granite() -> str:
    return generate_answer(
        question="Reply with exactly: Granite is working.",
        context="(none)",
        max_tokens=30,
    )
