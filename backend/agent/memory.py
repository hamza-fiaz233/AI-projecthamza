import backend.agent  # noqa: F401
import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.sqlite import SqliteSaver
from backend.config import settings

_checkpointer_instance: Optional[SqliteSaver] = None


def get_llm(temperature: float = 0.1):
    """
    Return the configured LLM client (Groq by default, OpenAI as fallback)
    with low temperature for reliable financial reasoning and tool calling.
    """
    provider = settings.LLM_PROVIDER.lower().strip()

    if provider == "openai":
        if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY == "your_openai_api_key_here":
            raise ValueError("OPENAI_API_KEY is missing in your .env file.")
        return ChatOpenAI(
            model=settings.OPENAI_MODEL,
            api_key=settings.OPENAI_API_KEY,
            temperature=temperature,
        )

    # Default: Groq free-tier LPU inference
    if not settings.GROQ_API_KEY or settings.GROQ_API_KEY == "your_groq_api_key_here":
        raise ValueError(
            "GROQ_API_KEY is missing in your .env file. Add your key to finai-analyst/.env first."
        )
    return ChatGroq(
        model=settings.GROQ_MODEL,
        api_key=settings.GROQ_API_KEY,
        temperature=temperature,
    )


def get_checkpointer() -> SqliteSaver:
    """Return a singleton SQLite checkpointer for LangGraph multi-turn session state."""
    global _checkpointer_instance
    if _checkpointer_instance is None:
        conn = sqlite3.connect(settings.SQLITE_DB_PATH, check_same_thread=False)
        saver = SqliteSaver(conn)
        saver.setup()
        _checkpointer_instance = saver
    return _checkpointer_instance


def init_session_table() -> None:
    """Create the SQLite chat_turns table for UI conversation logs and observability."""
    with sqlite3.connect(settings.SQLITE_DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_turns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                thread_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                intent TEXT,
                tool_calls TEXT,
                citations TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


def log_chat_turn(
    thread_id: str,
    role: str,
    content: str,
    intent: Optional[str] = None,
    tool_calls: Optional[List[str]] = None,
    citations: Optional[List[Dict[str, Any]]] = None,
) -> None:
    """Persist a user or assistant message turn into SQLite."""
    init_session_table()
    with sqlite3.connect(settings.SQLITE_DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO chat_turns (thread_id, role, content, intent, tool_calls, citations, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                thread_id,
                role,
                content,
                intent,
                json.dumps(tool_calls or []),
                json.dumps(citations or []),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()


def get_session_history(thread_id: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Retrieve recent turns for a given thread_id."""
    init_session_table()
    with sqlite3.connect(settings.SQLITE_DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT role, content, intent, tool_calls, citations, created_at
            FROM chat_turns
            WHERE thread_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (thread_id, limit),
        ).fetchall()
        results = []
        for r in reversed(rows):
            item = dict(r)
            item["tool_calls"] = json.loads(item["tool_calls"] or "[]")
            item["citations"] = json.loads(item["citations"] or "[]")
            results.append(item)
        return results
