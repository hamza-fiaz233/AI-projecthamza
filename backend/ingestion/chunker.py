import re
from typing import Any, Dict, List
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Regex pattern to detect SEC Form 10-K / 10-Q section headings
SEC_SECTION_PATTERN = re.compile(
    r"(?im)^(item\s+\d+[a-z]?\.?\s*[-–—:]?\s*[a-z0-9 ,&'()/-]{3,80})$"
)

# Canonical mapping for clean metadata filtering
CANONICAL_SECTIONS = {
    "item 1.": "Business Overview",
    "item 1a": "Risk Factors",
    "item 1b": "Unresolved Staff Comments",
    "item 1c": "Cybersecurity",
    "item 2": "Properties",
    "item 3": "Legal Proceedings",
    "item 5": "Market for Common Equity",
    "item 7": "MD&A",
    "item 7a": "Market Risk Disclosures",
    "item 8": "Financial Statements",
    "item 9a": "Controls and Procedures",
}


def detect_section_label(text: str, current_section: str = "General") -> str:
    """Detect if a page or paragraph introduces a new SEC Item heading."""
    matches = SEC_SECTION_PATTERN.findall(text)
    if not matches:
        return current_section

    latest_heading = re.sub(r"\s+", " ", matches[-1]).strip()
    lower_heading = latest_heading.lower()

    for prefix, canonical_name in CANONICAL_SECTIONS.items():
        if lower_heading.startswith(prefix):
            return canonical_name

    return latest_heading[:80]


def chunk_pages(
    pages: List[Dict[str, Any]],
    metadata: Dict[str, Any],
    chunk_size: int = 1000,
    chunk_overlap: int = 150,
) -> List[Document]:
    """
    Convert extracted page dicts into section-tagged LangChain Document chunks
    with full metadata (ticker, company, doc_type, fiscal_year, section, page, source_file).
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks: List[Document] = []
    active_section = "General"
    chunk_counter = 0

    base_meta = {
        "ticker": str(metadata.get("ticker", "UNKNOWN")).upper().strip(),
        "company": str(metadata.get("company", metadata.get("ticker", "Unknown Company"))).strip(),
        "doc_type": str(metadata.get("doc_type", "10-K")).strip(),
        "fiscal_year": int(metadata.get("fiscal_year", 2025)),
        "filing_date": str(metadata.get("filing_date", "")),
    }

    for page_obj in pages:
        page_num = int(page_obj["page"])
        page_text = page_obj["text"]
        source_file = page_obj.get("source_file", metadata.get("source_file", "unknown.pdf"))

        # Update active section if a new SEC Item heading appears on this page
        active_section = detect_section_label(page_text, active_section)

        page_doc = Document(
            page_content=page_text,
            metadata={
                **base_meta,
                "section": active_section,
                "page": page_num,
                "source_file": source_file,
            },
        )

        split_docs = splitter.split_documents([page_doc])
        for doc in split_docs:
            # Re-check if a heading appeared inside this specific sub-chunk
            doc.metadata["section"] = detect_section_label(doc.page_content, doc.metadata["section"])
            doc.metadata["chunk_index"] = chunk_counter
            chunks.append(doc)
            chunk_counter += 1

    return chunks
