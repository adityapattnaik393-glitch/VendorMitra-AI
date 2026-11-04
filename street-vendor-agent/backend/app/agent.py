import re

from app.rag import retrieve_context
from app.granite import generate_answer


_HINDI_SCRIPT = re.compile(r"[\u0900-\u097f]")


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
    profile_lines = []
    for key, value in (vendor_profile or {}).items():
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
            f"Content: {item['content']}"
            for item in results
        )
        if results
        else "No relevant verified source material is currently indexed."
    )

    answer = generate_answer(
        question=question,
        context=context,
        task=task,
        vendor_context=vendor_context,
        preferred_language=_response_language(question, preferred_language),
    )

    return {
        "answer": answer,
        "sources": list(
            dict.fromkeys(
                item["source"] for item in results
            )
        )
    }
