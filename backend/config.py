import os
from pathlib import Path
from dotenv import load_dotenv

# Resolve project root (finai-analyst/) regardless of current working directory
BASE_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = BASE_DIR / "backend"

# Load environment variables from root .env
load_dotenv(BASE_DIR / ".env")


class Settings:
    PROJECT_NAME: str = "FinAI Analyst"
    VERSION: str = "1.0.0"

    # LLM Provider Configuration ("groq" or "openai")
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "groq").lower()
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    # Embeddings & Storage Paths
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
    CHROMA_PERSIST_DIR: str = str(
        (BASE_DIR / os.getenv("CHROMA_PERSIST_DIR", "chroma_db")).resolve()
    )
    SQLITE_DB_PATH: str = str(
        (BASE_DIR / os.getenv("SQLITE_DB_PATH", "finai.db")).resolve()
    )
    DATA_DIR: str = str((BACKEND_DIR / "data").resolve())

    # Agent Guardrails & Limits
    MAX_AGENT_ITERATIONS: int = 3
    CHROMA_COLLECTION_NAME: str = "financial_docs"


settings = Settings()

# Ensure core directories exist on startup
os.makedirs(settings.DATA_DIR, exist_ok=True)
os.makedirs(settings.CHROMA_PERSIST_DIR, exist_ok=True)
