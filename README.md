# FinAI Analyst — Agentic RAG Chatbot for Live Stock & Finance Analysis

An end-to-end full-stack financial research assistant powered by **FastAPI**, **LangGraph**, **ChromaDB**, **yfinance**, and **React + Vite + Tailwind CSS**.

---

## Team Members & Module Ownership

| Member | Role & Module Ownership | Key Files |
| :--- | :--- | :--- |
| **Hamza Fiaz** *(Group Leader)* | LangGraph Orchestration, FastAPI Gateway & Full-Stack Integration | `backend/agent/graph.py`, `backend/api/server.py`, `frontend/src/App.jsx` |
| **Sidra Iqbal** | PDF Ingestion, SEC Section Chunker & ChromaDB Retrieval | `backend/ingestion/loader.py`, `chunker.py`, `pipeline.py`, `backend/tools/retrieval.py` |
| **Shumail Mhadi** | Live Market Data Tools & TTL Caching | `backend/tools/market_data.py` |
| **Areej Fatima** | Agent State, Prompts & SQLite Session Memory | `backend/agent/state.py`, `prompts.py`, `memory.py` |
| **Avisa Raheel** | Input/Output Guardrails & Pytest Evaluation Suite | `backend/agent/guardrails.py`, `backend/tests/test_smoke.py` |
| **Malaika Aziz** | React Financial Dashboard, Charts & Citation UI | `frontend/src/components/ChatWindow.jsx`, `StockChart.jsx`, `SourcePanel.jsx`, `PdfUploader.jsx` |

---

## Quick Start (Windows Command Prompt `cmd.exe`)

> **Windows Device Guard Rule:** Always run Python CLI tools with `python -m` instead of calling `.exe` wrappers directly inside `.venv\Scripts\`.

### 1. Backend Setup
```cmd
cd finai-analyst
py -3.11 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r backend\requirements.txt
python -m pip install --upgrade yfinance
copy .env.example .env
```
Add your `GROQ_API_KEY` inside `.env`, then start FastAPI:
```cmd
python -m uvicorn backend.api.server:app --reload --port 8000
```

### 2. Frontend Setup (Second Terminal)
```cmd
cd finai-analyst\frontend
npm install
npm run dev
```
Open **http://localhost:5173** in your browser.

### 3. Run Automated Tests
```cmd
python -m pytest -v
```
