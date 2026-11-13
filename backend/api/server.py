import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from backend.agent.graph import run_agent
from backend.agent.memory import get_session_history
from backend.config import settings
from backend.ingestion.pipeline import ingest_pdf, list_ingested_documents

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Agentic RAG Chatbot for Live Stock and Finance Analysis",
)

# Enable CORS so React Vite dev server (localhost:5173) can call FastAPI
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000, description="User financial question")
    thread_id: str = Field(default="default_session", min_length=1, max_length=100)


class ChatResponse(BaseModel):
    thread_id: str
    question: str
    answer: str
    intent: str
    tickers: List[str] = []
    tools_called: List[str] = []
    citations: List[Dict[str, Any]] = []
    api_timestamps: List[str] = []
    chart_data: Optional[Dict[str, Any]] = None
    latency_ms: float


@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "llm_provider": settings.LLM_PROVIDER,
        "model": settings.GROQ_MODEL if settings.LLM_PROVIDER == "groq" else settings.OPENAI_MODEL,
        "groq_key_configured": bool(
            settings.GROQ_API_KEY and settings.GROQ_API_KEY != "your_groq_api_key_here"
        ),
        "utc_timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/api/chat", response_model=ChatResponse)
def chat_endpoint(payload: ChatRequest):
    try:
        result = run_agent(question=payload.question.strip(), thread_id=payload.thread_id.strip())
        return ChatResponse(**result)
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Agent execution failed: {str(exc)}")


@app.post("/api/upload")
async def upload_pdf_endpoint(
    file: UploadFile = File(...),
    ticker: str = Form(...),
    company: str = Form(""),
    doc_type: str = Form("10-K"),
    fiscal_year: int = Form(2025),
    filing_date: str = Form(""),
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files (.pdf) are supported.")

    clean_ticker = ticker.strip().upper()
    if not clean_ticker:
        raise HTTPException(status_code=400, detail="Ticker symbol is required.")

    ticker_dir = Path(settings.DATA_DIR) / clean_ticker
    ticker_dir.mkdir(parents=True, exist_ok=True)
    safe_filename = Path(file.filename).name
    dest_path = ticker_dir / safe_filename

    try:
        with open(dest_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        result = ingest_pdf(
            file_path=dest_path,
            ticker=clean_ticker,
            company=company.strip() or clean_ticker,
            doc_type=doc_type.strip() or "10-K",
            fiscal_year=fiscal_year,
            filing_date=filing_date.strip(),
        )
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"PDF ingestion failed: {str(exc)}")
    finally:
        await file.close()


@app.get("/api/documents")
def get_documents_endpoint():
    docs = list_ingested_documents()
    return {"count": len(docs), "documents": docs}


@app.get("/api/history/{thread_id}")
def get_history_endpoint(thread_id: str, limit: int = 30):
    turns = get_session_history(thread_id=thread_id, limit=limit)
    return {"thread_id": thread_id, "count": len(turns), "messages": turns}
