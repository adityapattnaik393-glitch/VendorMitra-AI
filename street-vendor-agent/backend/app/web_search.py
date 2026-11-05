"""Live retrieval of relevant content from allowlisted government websites."""
from datetime import datetime, timezone
import logging
import os
from urllib.parse import urlsplit

import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)
TAVILY_URL = "https://api.tavily.com/search"
TAVILY_API_KEY = (os.getenv("TAVILY_API_KEY") or "").strip()
OFFICIAL_DOMAINS = (
    "myscheme.gov.in",
    "pmsvanidhi.mohua.gov.in",
    "udyamregistration.gov.in",
    "mudra.org.in",
    "mohua.gov.in",
)


def _is_official_https_url(url: str) -> bool:
    try:
        parsed = urlsplit(url)
        hostname = (parsed.hostname or "").lower().rstrip(".")
    except ValueError:
        return False
    return (
        parsed.scheme == "https"
        and not parsed.username
        and not parsed.password
        and any(
            hostname == domain or hostname.endswith(f".{domain}")
            for domain in OFFICIAL_DOMAINS
        )
    )


def search_official_sources(question: str) -> dict[str, object]:
    """Search official sites and return extracted page content with provenance metadata."""
    if not TAVILY_API_KEY:
        logger.warning("Official-site search unavailable: TAVILY_API_KEY is not configured.")
        return {"results": [], "error": "TAVILY_API_KEY is not configured."}

    try:
        response = requests.post(
            TAVILY_URL,
            json={
                "api_key": TAVILY_API_KEY,
                "query": question,
                "search_depth": "advanced",
                "include_domains": list(OFFICIAL_DOMAINS),
                "include_raw_content": "markdown",
                "max_results": 5,
            },
            timeout=25,
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as error:
        logger.warning("Official-site search failed: %s", error)
        return {"results": [], "error": "Official website search failed."}

    raw_results = payload.get("results", []) if isinstance(payload, dict) else []
    retrieved_at = datetime.now(timezone.utc)
    metadata_date = retrieved_at.date().isoformat()
    retrieval_date = retrieved_at.isoformat(timespec="seconds").replace("+00:00", "Z")
    results = []
    if isinstance(raw_results, list):
        for result in raw_results:
            if not isinstance(result, dict):
                continue
            url = result.get("url")
            if not isinstance(url, str) or not _is_official_https_url(url):
                continue
            content = result.get("raw_content") or result.get("content")
            if not isinstance(content, str) or not content.strip():
                continue
            title = result.get("title")
            title = title.strip() if isinstance(title, str) and title.strip() else url
            metadata = {
                "source_type": "official_web",
                "source_url": url,
                "document_title": title,
                "retrieval_date": retrieval_date,
                "last_verified_date": metadata_date,
            }
            results.append({"content": content.strip()[:3500], "metadata": metadata})

    if not results:
        logger.warning("Official-site search returned no usable allowlisted content.")
        return {"results": [], "error": "No relevant official website content was found."}
    return {"results": results, "error": None}
