"""Check IBM credentials, available Granite models, and one real model call."""
import sys

import requests

from app import granite


def _step(ok: bool, text: str) -> bool:
    print(("  [PASS] " if ok else "  [FAIL] ") + text)
    return ok


def main() -> int:
    print(f"Region : {granite.IBM_REGION}  ({granite.WATSONX_URL})")
    print(f"Model  : {granite.IBM_MODEL_ID}\n")

    print("1) .env values")
    problems = granite.config_problems()
    if not _step(not problems, "IBM_API_KEY and IBM_PROJECT_ID are set" if not problems else "; ".join(problems)):
        return 1

    print("2) IBM IAM login")
    try:
        granite.get_iam_token(force_refresh=True)
        _step(True, "API key accepted, bearer token received")
    except granite.GraniteError as error:
        _step(False, str(error))
        return 1

    print("3) Granite models served in your region")
    try:
        models = granite.list_available_chat_models()
        if not models:
            print("  [WARN] no available Granite chat models are listed for this region.")
        for model_id in models:
            print(f"      {model_id:<40} available   chat")
        if models and granite.IBM_MODEL_ID not in models:
            print(
                f"  [WARN] '{granite.IBM_MODEL_ID}' is not available chat in this region; "
                "set IBM_MODEL_ID in backend/.env to one listed above."
            )
    except (granite.GraniteError, requests.RequestException, ValueError) as error:
        print(f"  [WARN] could not list models: {error}")

    print("4) Real Granite call")
    try:
        answer = granite.test_granite()
        _step(True, f"Granite answered: {answer!r}")
    except granite.GraniteError as error:
        _step(False, str(error))
        return 1

    print("\nAll good - IBM Granite is integrated and responding.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())