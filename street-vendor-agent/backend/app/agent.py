import re

from app.rag import retrieve_context
from app.granite import generate_answer


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

    context = (
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

    answer = generate_answer(
        question=question,
        context=context,
        task=_infer_task(question, task),
        vendor_context=vendor_context,
        preferred_language=_response_language(question, preferred_language),
    )

    return {
        "answer": answer,
        "vendor_profile": vendor_profile,
        "sources": list(
            dict.fromkeys(
                (
                    f"{item['source']} — {item['source_date']}"
                    if item.get("source_date")
                    else item["source"]
                )
                for item in results
            )
        ),
    }
