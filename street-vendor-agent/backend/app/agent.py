from app.rag import retrieve_context
from app.granite import generate_answer


def ask_vendor_mitra(question):

    results = retrieve_context(question)

    if not results:
        return {
            "answer": "I could not find verified information.",
            "sources": []
        }

    context = "\n\n".join(
        f"Source: {item['source']}\n"
        f"Content: {item['content']}"
        for item in results
    )

    answer = generate_answer(
        question=question,
        context=context
    )

    return {
        "answer": answer,
        "sources": list(
            dict.fromkeys(
                item["source"] for item in results
            )
        )
    }
