from typing import Any, Dict, List, Optional
from langchain_core.tools import tool
from backend.ingestion.pipeline import get_vectorstore, list_ingested_documents


@tool
def retrieve_filings(
    query: str,
    ticker: Optional[str] = None,
    doc_type: Optional[str] = None,
    year: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Search ingested SEC filings (10-K, 10-Q, 8-K) and earnings transcripts for relevant passages.
    Use this for questions about risk factors, management guidance, MD&A, strategy, or segment performance.
    """
    vectordb = get_vectorstore()

    # Build Chroma metadata filter cleanly
    conditions: List[Dict[str, Any]] = []
    if ticker and ticker.strip():
        conditions.append({"ticker": ticker.strip().upper()})
    if doc_type and doc_type.strip():
        conditions.append({"doc_type": doc_type.strip()})
    if year is not None:
        conditions.append({"fiscal_year": int(year)})

    where_filter: Optional[Dict[str, Any]] = None
    if len(conditions) == 1:
        where_filter = conditions[0]
    elif len(conditions) > 1:
        where_filter = {"$and": conditions}

    try:
        docs = vectordb.max_marginal_relevance_search(
            query=query,
            k=5,
            fetch_k=20,
            filter=where_filter,
        )
    except Exception as exc:
        return {
            "query": query,
            "matches": [],
            "message": f"Vector retrieval error: {str(exc)}",
        }

    # Fallback without strict doc_type/year filter if ticker-filtered search returns nothing
    if not docs and ticker and len(conditions) > 1:
        try:
            docs = vectordb.max_marginal_relevance_search(
                query=query,
                k=5,
                fetch_k=20,
                filter={"ticker": ticker.strip().upper()},
            )
        except Exception:
            docs = []

    if not docs:
        indexed = list_ingested_documents()
        available_tickers = sorted({d["ticker"] for d in indexed})
        return {
            "query": query,
            "matches": [],
            "message": (
                f"No indexed filing passages found matching your filter. "
                f"Currently indexed tickers: {available_tickers if available_tickers else 'None'}."
            ),
        }

    results: List[Dict[str, Any]] = []
    for d in docs:
        meta = d.metadata or {}
        source_file = meta.get("source_file", "unknown.pdf")
        page = meta.get("page", 1)
        results.append({
            "text": d.page_content,
            "ticker": meta.get("ticker"),
            "company": meta.get("company"),
            "doc_type": meta.get("doc_type"),
            "fiscal_year": meta.get("fiscal_year"),
            "section": meta.get("section", "General"),
            "page": page,
            "source_file": source_file,
            "citation": f"[Source: {source_file}, p.{page}]",
        })

    return {
        "query": query,
        "match_count": len(results),
        "matches": results,
    }
