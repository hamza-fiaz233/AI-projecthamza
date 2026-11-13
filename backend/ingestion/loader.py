import hashlib
import re
from pathlib import Path
from typing import Any, Dict, List
import fitz  # PyMuPDF
import pdfplumber


def compute_file_hash(file_path: str | Path) -> str:
    """Compute SHA-256 hash of a PDF file to prevent duplicate ingestion."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for block in iter(lambda: f.read(65536), b""):
            sha256.update(block)
    return sha256.hexdigest()


def clean_financial_text(text: str) -> str:
    """Clean extracted PDF text: repair hyphenated line breaks and normalize whitespace."""
    if not text:
        return ""
    # Repair words broken across lines with hyphens (e.g., "rev-\nenue" -> "revenue")
    text = re.sub(r"(\w+)-\n(\w+)", r"\1\2", text)
    # Remove standalone page number lines
    text = re.sub(r"(?m)^\s*(?:Page\s+)?\d+\s*(?:of\s+\d+)?\s*$", "", text, flags=re.IGNORECASE)
    # Collapse excessive blank lines and spaces while keeping paragraph breaks
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _extract_tables_as_pipes(pdf_path: str | Path) -> Dict[int, str]:
    """Use pdfplumber to extract financial tables into pipe-delimited Markdown-style rows per 1-based page."""
    page_tables: Dict[int, str] = {}
    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            for idx, page in enumerate(pdf.pages, start=1):
                tables = page.extract_tables()
                if not tables:
                    continue
                formatted_tables: List[str] = []
                for table in tables:
                    rows_text: List[str] = []
                    for row in table:
                        if not row:
                            continue
                        cleaned_cells = [
                            re.sub(r"\s+", " ", cell.strip()) if cell else ""
                            for cell in row
                        ]
                        if any(cleaned_cells):
                            rows_text.append("| " + " | ".join(cleaned_cells) + " |")
                    if len(rows_text) >= 2:
                        formatted_tables.append("\n".join(rows_text))
                if formatted_tables:
                    page_tables[idx] = "\n\n[Extracted Table]\n" + "\n\n".join(formatted_tables)
    except Exception:
        # Fallback gracefully if pdfplumber encounters malformed table layout
        pass
    return page_tables


def load_pdf_pages(file_path: str | Path) -> List[Dict[str, Any]]:
    """
    Extract cleaned text and pipe-delimited tables from every page of a PDF.
    Returns a list of dicts: [{'page': 1, 'text': '...', 'source_file': 'AAPL_10K.pdf'}, ...]
    """
    path = Path(file_path)
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"PDF file not found: {path}")

    table_map = _extract_tables_as_pipes(path)
    pages_output: List[Dict[str, Any]] = []

    with fitz.open(str(path)) as doc:
        for page_index in range(len(doc)):
            page_num = page_index + 1
            raw_text = doc[page_index].get_text("text") or ""
            cleaned = clean_financial_text(raw_text)

            if page_num in table_map:
                cleaned = f"{cleaned}\n{table_map[page_num]}".strip()

            if cleaned:
                pages_output.append({
                    "page": page_num,
                    "text": cleaned,
                    "source_file": path.name,
                })

    return pages_output
