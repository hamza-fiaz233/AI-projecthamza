import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
from langchain_community.vectorstores import Chroma
from langchain_core.embeddings import Embeddings
from backend.config import settings
from backend.ingestion.chunker import chunk_pages
from backend.ingestion.loader import compute_file_hash, load_pdf_pages


class ChromaONNXEmbeddings(Embeddings):
    """Lightweight 384-dim local ONNX embedding wrapper (no PyTorch DLLs required)."""

    def __init__(self) -> None:
        self._ef = DefaultEmbeddingFunction()

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        return [[float(x) for x in vec] for vec in self._ef(texts)]

    def embed_query(self, text: str) -> List[float]:
        return [float(x) for x in self._ef([text])[0]]


# Cached singletons so embedding model and Chroma client load once
_embeddings_instance: Optional[Embeddings] = None
_vectordb_instance: Optional[Chroma] = None


def get_embeddings() -> Embeddings:
    global _embeddings_instance
    if _embeddings_instance is None:
        _embeddings_instance = ChromaONNXEmbeddings()
    return _embeddings_instance


def get_vectorstore() -> Chroma:
    global _vectordb_instance
    if _vectordb_instance is None:
        _vectordb_instance = Chroma(
            collection_name=settings.CHROMA_COLLECTION_NAME,
            embedding_function=get_embeddings(),
            persist_directory=settings.CHROMA_PERSIST_DIR,
        )
    return _vectordb_instance


def init_document_registry() -> None:
    """Create the SQLite documents registry table if it does not exist."""
    with sqlite3.connect(settings.SQLITE_DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                doc_id TEXT PRIMARY KEY,
                source_file TEXT NOT NULL,
                ticker TEXT NOT NULL,
                company TEXT,
                doc_type TEXT NOT NULL,
                fiscal_year INTEGER,
                file_hash TEXT UNIQUE NOT NULL,
                chunk_count INTEGER NOT NULL,
                embedding_model TEXT NOT NULL,
                ingested_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


def is_already_ingested(file_hash: str) -> Optional[Dict[str, Any]]:
    init_document_registry()
    with sqlite3.connect(settings.SQLITE_DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM documents WHERE file_hash = ?", (file_hash,)
        ).fetchone()
        return dict(row) if row else None


def list_ingested_documents() -> List[Dict[str, Any]]:
    """Return all indexed PDF documents from SQLite registry."""
    init_document_registry()
    with sqlite3.connect(settings.SQLITE_DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT doc_id, source_file, ticker, company, doc_type, fiscal_year, chunk_count, ingested_at FROM documents ORDER BY ingested_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def ingest_pdf(
    file_path: str | Path,
    ticker: str,
    company: str = "",
    doc_type: str = "10-K",
    fiscal_year: int = 2025,
    filing_date: str = "",
    force_reindex: bool = False,
) -> Dict[str, Any]:
    """
    End-to-end ingestion of a financial PDF into ChromaDB and SQLite registry.
    Skips duplicate files by SHA-256 hash unless force_reindex=True.
    """
    init_document_registry()
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF file not found: {path}")

    file_hash = compute_file_hash(path)
    existing = is_already_ingested(file_hash)
    if existing and not force_reindex:
        return {
            "status": "skipped_duplicate",
            "message": f"'{path.name}' is already indexed ({existing['chunk_count']} chunks).",
            "document": existing,
        }

    pages = load_pdf_pages(path)
    if not pages:
        raise ValueError(f"No extractable text found in '{path.name}'.")

    clean_ticker = ticker.strip().upper()
    clean_company = company.strip() or clean_ticker
    doc_id = f"{clean_ticker}_{doc_type}_{fiscal_year}_{uuid.uuid4().hex[:8]}"

    metadata = {
        "doc_id": doc_id,
        "ticker": clean_ticker,
        "company": clean_company,
        "doc_type": doc_type.strip(),
        "fiscal_year": int(fiscal_year),
        "filing_date": filing_date.strip(),
        "source_file": path.name,
    }

    chunks = chunk_pages(pages, metadata=metadata)
    for c in chunks:
        c.metadata["doc_id"] = doc_id

    chunk_ids = [f"{doc_id}_chunk_{c.metadata['chunk_index']}" for c in chunks]
    vectordb = get_vectorstore()
    vectordb.add_documents(documents=chunks, ids=chunk_ids)

    ingested_at = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(settings.SQLITE_DB_PATH) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO documents
            (doc_id, source_file, ticker, company, doc_type, fiscal_year, file_hash, chunk_count, embedding_model, ingested_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                doc_id,
                path.name,
                clean_ticker,
                clean_company,
                doc_type.strip(),
                int(fiscal_year),
                file_hash,
                len(chunks),
                "onnx-all-MiniLM-L6-v2",
                ingested_at,
            ),
        )
        conn.commit()

    return {
        "status": "ingested",
        "message": f"Successfully indexed '{path.name}' into {len(chunks)} chunks.",
        "document": {
            "doc_id": doc_id,
            "source_file": path.name,
            "ticker": clean_ticker,
            "company": clean_company,
            "doc_type": doc_type.strip(),
            "fiscal_year": int(fiscal_year),
            "chunk_count": len(chunks),
            "ingested_at": ingested_at,
        },
    }
