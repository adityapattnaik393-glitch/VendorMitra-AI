import logging
import re

from app.rag import retrieve_context
from app.granite import GraniteError, generate_answer, needs_live_search
from app.web_search import search_official_sources

logger = logging.getLogger(__name__)

_HINDI_SCRIPT = re.compile(r"[\u0900-\u097f]")
_PROFILE_PATTERNS = (
    re.compile(
        r"\bi\s+(?:sell|sells)\s+(?P<products>[^,.!?]+?)\s+"
        r"(?:in|at|around|near)\s+(?P<location>[^,.!?]+)",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bi\s+(?:run|own|have)\s+(?:a|an)\s+"
        r"(?P<business>[^,.!?]+?)\s+(?:in|at|around|near)\s+"
        r"(?P<location>[^,.!?]+)",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bmai(?:n)?\s+(?P<location>.+?)\s+me\s+"
        r"(?P<products>.+?)\s+bechta(?:i)?\s+hu\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:मैं|हम)\s+(?P<location>.+?)\s+में\s+"
        r"(?P<products>.+?)\s+बेच(?:ता|ती|ते)\s+(?:हूँ|हूं|है|हैं)",
    ),
)
_PROFILE_INTENT = re.compile(
    r"\b(?:business\s+profile|profile\s+for\s+my|write\s+my\s+profile|"
    r"create\s+(?:a\s+)?profile|generate\s+(?:a\s+)?profile|"
    r"draft\s+(?:a\s+)?profile|make\s+(?:me\s+)?(?:a\s+)?(?:vendor\s+)?profile)\b",
    re.IGNORECASE,
)
_HINDI_PROFILE_INTENT = re.compile(
    r"(?:व्यवसाय|बिज़नेस|बिज़नेस|दुकान|स्टॉल).{0,30}(?:प्रोफ़ाइल|प्रोफाइल|परिचय)|"
    r"(?:प्रोफ़ाइल|प्रोफाइल|परिचय).{0,25}(?:बनाओ|बनाएं|लिखो|तैयार)",
)
_PROMOTION_INTENT = re.compile(
    r"\b(?:promot(?:e|ion|ional)|advert(?:ise|isement)|whatsapp\s+message|"
    r"signboard|qr\s*(?:code\s*)?poster)\b",
    re.IGNORECASE,
)
_HINDI_PROMOTION_INTENT = re.compile(r"प्रचार|विज्ञापन|व्हाट्सएप|पोस्टर|बैनर")
_SCHEME_INTENT = re.compile(
    r"\b(?:government|govt|central|state|scheme|yojana|myscheme|"
    r"pm\s*svanidhi|pmsvanidhi|svanidhi|mudra|udyam|benefit|subsidy|loan|"
    r"grant|eligibility|eligible|application|deadline|last\s+date|interest\s+rate|"
    r"financial\s+assistance)\b|योजना|सरकार|सरकारी|लाभ|सब्सिडी|लोन|कर्ज|ऋण|"
    r"अनुदान|सहायता|पात्रता|आवेदन|आखिरी\s+तारीख|अंतिम\s+तारीख|ब्याज\s+दर",
    re.IGNORECASE,
)
_LIVE_REFERENCE_INTENT = re.compile(
    r"\b(?:current|currently|latest|recent|today|now|updated|new\s+rules|"
    r"eligibility|eligible|apply|application|deadline|last\s+date|amount|"
    r"interest\s+rate|benefit|subsidy|source|reference|citation|link|"
    r"official\s+(?:website|source))\b|अभी|वर्तमान|नवीनतम|आज|ताज़ा|ताजा|"
    r"पात्रता|पात्र|आवेदन|आखिरी\s+तारीख|अंतिम\s+तारीख|राशि|ब्याज|लाभ|"
    r"स्रोत|लिंक|आधिकारिक\s+(?:वेबसाइट|स्रोत)",
    re.IGNORECASE,
)


def _infer_task(question: str, task: str) -> str:
    if task != "general":
        return task
    if _PROFILE_INTENT.search(question) or _HINDI_PROFILE_INTENT.search(question):
        return "business_profile"
    if _PROMOTION_INTENT.search(question) or _HINDI_PROMOTION_INTENT.search(question):
        return "promotional_materials"
    return task


def _extract_vendor_profile(
    question: str,
    vendor_profile: dict[str, object] | None,
) -> dict[str, object]:
    profile = dict(vendor_profile or {})
    if profile.get("location") and (profile.get("products") or profile.get("business_type")):
        return profile

    for pattern in _PROFILE_PATTERNS:
        match = pattern.search(question)
        if not match:
            continue
        location = match.group("location").strip().removesuffix(" area").strip()
        location = re.sub(r"'s\s+", " ", location)
        if location and not profile.get("location"):
            profile["location"] = location
        products = match.groupdict().get("products")
        business = match.groupdict().get("business")
        if products and not profile.get("products"):
            product = products.strip()
            profile["products"] = [product]
            if not profile.get("business_type"):
                profile["business_type"] = (
                    f"{product} विक्रेता"
                    if _HINDI_SCRIPT.search(product)
                    else f"{product.title()} seller"
                )
        elif business and not profile.get("business_type"):
            profile["business_type"] = business.strip().title()
        break
    return profile


def _response_language(question: str, preferred_language: str) -> str:
    if _HINDI_SCRIPT.search(question):
        return "Hindi"
    return preferred_language


def ask_vendor_mitra(
    question: str,
    task: str = "general",
    vendor_profile: dict[str, object] | None = None,
    preferred_language: str = "English",
):
    vendor_profile = _extract_vendor_profile(question, vendor_profile)
    profile_lines = []
    for key, value in vendor_profile.items():
        if value:
            formatted_value = (
                ", ".join(str(item) for item in value)
                if isinstance(value, list)
                else str(value)
            )
            profile_lines.append(f"{key.replace('_', ' ').title()}: {formatted_value}")

    vendor_context = "\n".join(profile_lines)
    retrieval_query = f"{question}\n{vendor_context}" if vendor_context else question

    results = retrieve_context(retrieval_query)

    stored_context = (
        "\n\n".join(
            f"Source: {item['source']}\n"
            + (
                f"Source date: {item['source_date']}\n"
                if item.get("source_date")
                else ""
            )
            + f"Content: {item['content']}"
            for item in results
        )
        if results
        else "No relevant verified source material is currently indexed."
    )

    online_results = []
    online_error = None
    effective_task = _infer_task(question, task)
    if _SCHEME_INTENT.search(question) and effective_task not in {
        "business_profile",
        "promotional_materials",
    }:
        try:
            granite_decision = needs_live_search(question, stored_context)
        except GraniteError as error:
            logger.warning(
                "Granite live-search decision failed; trying official-site search: %s",
                error,
            )
            granite_decision = True
        if granite_decision or _LIVE_REFERENCE_INTENT.search(question):
            online_result = search_official_sources(question)
            online_results = online_result["results"]
            online_error = online_result["error"]

    context_sections = [f"[STORED PDF INFORMATION]\n{stored_context}"]
    for item in online_results:
        metadata = item["metadata"]
        context_sections.append(
            "[NEWLY RETRIEVED OFFICIAL WEBSITE INFORMATION]\n"
            f"Document title: {metadata['document_title']}\n"
            f"Source URL: {metadata['source_url']}\n"
            f"Retrieval date: {metadata['retrieval_date']}\n"
            f"Last verified date: {metadata['last_verified_date']}\n"
            f"Content: {item['content']}"
        )
    if online_error:
        context_sections.append(
            "[ONLINE VERIFICATION STATUS]\n"
            "Official online information could not be retrieved or verified for this "
            "question. Do not imply that current details were checked."
        )
    context = "\n\n".join(context_sections)

    answer = generate_answer(
        question=question,
        context=context,
        task=effective_task,
        vendor_context=vendor_context,
        preferred_language=_response_language(question, preferred_language),
    )
    if online_error:
        verification_note = (
            "\n\nऑनलाइन पुष्टि: अभी आधिकारिक सरकारी वेबसाइटों पर इस जानकारी की पुष्टि "
            "नहीं हो सकी।"
            if _response_language(question, preferred_language) == "Hindi"
            else "\n\nOnline verification: I couldn't verify this information on official "
            "government websites just now."
        )
        answer += verification_note

    source_labels = [
        (
            f"Stored document — {item['source']} — {item['source_date']}"
            if item.get("source_date")
            else f"Stored document — {item['source']}"
        )
        for item in results
    ]
    online_sources = [
        {
            "source_type": item["metadata"]["source_type"],
            "title": item["metadata"]["document_title"],
            "url": item["metadata"]["source_url"],
            "retrieval_date": item["metadata"]["retrieval_date"],
            "last_verified_date": item["metadata"]["last_verified_date"],
        }
        for item in online_results
    ]
    return {
        "answer": answer,
        "vendor_profile": vendor_profile,
        "sources": list(dict.fromkeys(source_labels)) + online_sources,
    }
