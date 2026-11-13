import fitz
from fastapi.testclient import TestClient
from backend.agent.guardrails import guardrail_in, guardrail_out
from backend.api.server import app
from backend.ingestion.chunker import chunk_pages
from backend.tools.market_data import get_quote

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "utc_timestamp" in data


def test_documents_endpoint():
    response = client.get("/api/documents")
    assert response.status_code == 200
    data = response.json()
    assert "count" in data
    assert isinstance(data["documents"], list)


def test_guardrail_in_blocks_advice_and_offtopic():
    allowed_advice, intent_advice, _ = guardrail_in("Should I buy Apple stock today?")
    assert allowed_advice is False
    assert intent_advice == "ADVICE_REQUEST"

    allowed_offtopic, intent_offtopic, _ = guardrail_in("Tell me a joke about cats")
    assert allowed_offtopic is False
    assert intent_offtopic == "OFF_TOPIC"

    allowed_valid, _, _ = guardrail_in("What is MSFT trailing P/E ratio?")
    assert allowed_valid is True


def test_guardrail_out_appends_citations_and_disclaimer():
    draft = "Apple reported supply chain dependencies in Asia."
    docs = [{"citation": "[Source: AAPL_10K.pdf, p.12]", "source_file": "AAPL_10K.pdf", "page": 12}]
    checked = guardrail_out(draft, tool_results=[], retrieved_docs=docs)
    assert "[Source: AAPL_10K.pdf, p.12]" in checked
    assert "Disclaimer: FinAI Analyst" in checked


def test_chunker_detects_sec_sections():
    pages = [
        {
            "page": 5,
            "text": "Item 1A. Risk Factors\nForeign currency fluctuations may reduce net sales.",
            "source_file": "TEST_10K.pdf",
        }
    ]
    chunks = chunk_pages(pages, {"ticker": "TEST", "company": "Test Corp", "doc_type": "10-K", "fiscal_year": 2025})
    assert len(chunks) == 1
    assert chunks[0].metadata["section"] == "Risk Factors"
    assert chunks[0].metadata["ticker"] == "TEST"


def test_live_quote_tool():
    res = get_quote.invoke({"ticker": "AAPL"})
    assert res["ticker"] == "AAPL"
    assert "as_of_utc" in res
    assert "price" in res or "error" in res


def test_pdf_upload_endpoint(tmp_path):
    pdf_path = tmp_path / "NVDA_10Q_test.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Item 7. Management Discussion and Analysis\nData center revenue grew significantly.")
    doc.save(str(pdf_path))
    doc.close()

    with open(pdf_path, "rb") as f:
        response = client.post(
            "/api/upload",
            data={"ticker": "NVDA", "company": "NVIDIA Corp", "doc_type": "10-Q", "fiscal_year": "2026"},
            files={"file": ("NVDA_10Q_test.pdf", f, "application/pdf")},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"ingested", "skipped_duplicate"}
