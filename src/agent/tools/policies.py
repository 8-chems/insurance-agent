from src.rag.retrieval import search


def search_policy_documents(question: str, expense_date: str) -> dict:
    """Search approved insurance policy text. expense_date is the date the
    expense occurred (YYYY-MM-DD) so the correct policy version is used.
    Use for any question about coverage, limits, waiting periods or rules."""
    hits = search(question, as_of=expense_date)
    return {"success": True, "passages": [
        {"source_id": h["chunk_id"], "version": h["version"], "section": h["section"],
         "page": h["page"], "text": h["text"]} for h in hits]}
