import axios from "axios";

const API_BASE_URL = "http://127.0.0";

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000,
});

export async function checkHealth() {
  const response = await apiClient.get("/health");
  return response.data;
}

export async function sendChatMessage(question, threadId) {
  const response = await apiClient.post("/chat", {
    question,
    thread_id: threadId,
  });
  return response.data;
}

export async function uploadFinancialPdf({
  file,
  ticker,
  company = "",
  docType = "10-K",
  fiscalYear = 2025,
  filingDate = "",
}) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("ticker", ticker);
  formData.append("company", company);
  formData.append("doc_type", docType);
  formData.append("fiscal_year", String(fiscalYear));
  formData.append("filing_date", filingDate);

  const response = await apiClient.post("/upload", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
  return response.data;
}

export async function fetchDocuments() {
  const response = await apiClient.get("/documents");
  return response.data;
}

export async function fetchChatHistory(threadId) {
  const response = await apiClient.get(`/history/${encodeURIComponent(threadId)}`);
  return response.data;
}
