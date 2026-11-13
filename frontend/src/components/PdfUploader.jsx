import React, { useEffect, useState } from "react";
import { Upload, FileCheck2, AlertCircle, Loader2, Database } from "lucide-react";
import { fetchDocuments, uploadFinancialPdf } from "../services/api";

export default function PdfUploader({ darkMode }) {
  const [file, setFile] = useState(null);
  const [ticker, setTicker] = useState("");
  const [company, setCompany] = useState("");
  const [docType, setDocType] = useState("10-K");
  const [fiscalYear, setFiscalYear] = useState(2025);
  const [uploading, setUploading] = useState(false);
  const [statusMsg, setStatusMsg] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [loadingDocs, setLoadingDocs] = useState(false);

  const loadDocs = async () => {
    setLoadingDocs(true);
    try {
      const data = await fetchDocuments();
      setDocuments(data.documents || []);
    } catch {
      setDocuments([]);
    } finally {
      setLoadingDocs(false);
    }
  };

  useEffect(() => {
    loadDocs();
  }, []);

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file || !ticker.trim()) {
      setStatusMsg({ type: "error", text: "Please select a PDF file and enter a ticker." });
      return;
    }

    setUploading(true);
    setStatusMsg(null);
    try {
      const res = await uploadFinancialPdf({
        file,
        ticker: ticker.trim().toUpperCase(),
        company: company.trim(),
        docType,
        fiscalYear,
      });
      setStatusMsg({
        type: "success",
        text: res.message || `Indexed ${file.name} successfully.`,
      });
      setFile(null);
      const inputEl = document.getElementById("pdf-file-input");
      if (inputEl) inputEl.value = "";
      await loadDocs();
    } catch (err) {
      const detail = err?.response?.data?.detail || err.message || "Upload failed.";
      setStatusMsg({ type: "error", text: detail });
    } finally {
      setUploading(false);
    }
  };

  const inputClass = `w-full rounded-lg border px-2.5 py-1.5 text-xs outline-none transition-colors ${
    darkMode
      ? "border-slate-700 bg-slate-900 text-slate-100 focus:border-emerald-500"
      : "border-slate-300 bg-white text-slate-900 focus:border-emerald-600"
  }`;

  return (
    <div className="flex flex-col gap-4">
      <form
        onSubmit={handleUpload}
        className={`rounded-xl border p-3.5 ${
          darkMode
            ? "border-slate-800 bg-slate-900/70 text-slate-100"
            : "border-slate-200 bg-white text-slate-900"
        }`}
      >
        <div className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-emerald-500">
          <Upload size={14} />
          <span>Ingest SEC Filing (PDF)</span>
        </div>

        <div className="space-y-2.5">
          <div>
            <label className="mb-1 block text-[11px] font-medium opacity-80">
              PDF File *
            </label>
            <input
              id="pdf-file-input"
              type="file"
              accept=".pdf,application/pdf"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              className="w-full cursor-pointer text-xs file:mr-2.5 file:rounded-md file:border-0 file:bg-emerald-600 file:px-2.5 file:py-1 file:text-xs file:font-medium file:text-white hover:file:bg-emerald-500"
            />
          </div>

          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="mb-1 block text-[11px] font-medium opacity-80">
                Ticker *
              </label>
              <input
                type="text"
                placeholder="AAPL"
                value={ticker}
                onChange={(e) => setTicker(e.target.value.toUpperCase())}
                className={inputClass}
              />
            </div>

            <div>
              <label className="mb-1 block text-[11px] font-medium opacity-80">
                Doc Type
              </label>
              <select
                value={docType}
                onChange={(e) => setDocType(e.target.value)}
                className={inputClass}
              >
                <option value="10-K">10-K</option>
                <option value="10-Q">10-Q</option>
                <option value="8-K">8-K</option>
                <option value="Transcript">Transcript</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="mb-1 block text-[11px] font-medium opacity-80">
                Company
              </label>
              <input
                type="text"
                placeholder="Apple Inc."
                value={company}
                onChange={(e) => setCompany(e.target.value)}
                className={inputClass}
              />
            </div>

            <div>
              <label className="mb-1 block text-[11px] font-medium opacity-80">
                Fiscal Year
              </label>
              <input
                type="number"
                min="2000"
                max="2030"
                value={fiscalYear}
                onChange={(e) => setFiscalYear(Number(e.target.value))}
                className={inputClass}
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={uploading}
            className="mt-1 flex w-full items-center justify-center gap-1.5 rounded-lg bg-emerald-600 px-3 py-2 text-xs font-semibold text-white transition hover:bg-emerald-500 disabled:opacity-50"
          >
            {uploading ? (
              <>
                <Loader2 size={14} className="animate-spin" />
                <span>Indexing Chunks...</span>
              </>
            ) : (
              <>
                <Upload size={14} />
                <span>Upload & Index PDF</span>
              </>
            )}
          </button>
        </div>

        {statusMsg && (
          <div
            className={`mt-2.5 flex items-start gap-1.5 rounded-lg p-2 text-xs ${
              statusMsg.type === "success"
                ? "bg-emerald-500/15 text-emerald-400"
                : "bg-rose-500/15 text-rose-400"
            }`}
          >
            {statusMsg.type === "success" ? (
              <FileCheck2 size={14} className="mt-0.5 shrink-0" />
            ) : (
              <AlertCircle size={14} className="mt-0.5 shrink-0" />
            )}
            <span>{statusMsg.text}</span>
          </div>
        )}
      </form>

      <div
        className={`rounded-xl border p-3.5 ${
          darkMode
            ? "border-slate-800 bg-slate-900/70 text-slate-100"
            : "border-slate-200 bg-white text-slate-900"
        }`}
      >
        <div className="mb-2.5 flex items-center justify-between">
          <div className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-sky-400">
            <Database size={14} />
            <span>Indexed Filings ({documents.length})</span>
          </div>
          <button
            type="button"
            onClick={loadDocs}
            className="text-[11px] opacity-70 hover:opacity-100"
          >
            Refresh
          </button>
        </div>

        {loadingDocs ? (
          <p className="text-xs opacity-60">Loading registry...</p>
        ) : documents.length === 0 ? (
          <p className="text-xs opacity-60">
            No filings indexed yet. Upload a 10-K or 10-Q PDF above.
          </p>
        ) : (
          <ul className="max-h-56 space-y-2 overflow-y-auto pr-1">
            {documents.map((doc) => (
              <li
                key={doc.doc_id}
                className={`rounded-lg border p-2 text-xs ${
                  darkMode
                    ? "border-slate-800 bg-slate-950/60"
                    : "border-slate-200 bg-slate-50"
                }`}
              >
                <div className="flex items-center justify-between font-semibold">
                  <span className="text-emerald-400">{doc.ticker}</span>
                  <span className="rounded bg-slate-800 px-1.5 py-0.5 text-[10px] text-slate-300">
                    {doc.doc_type} • FY{doc.fiscal_year}
                  </span>
                </div>
                <p className="mt-0.5 truncate opacity-90" title={doc.source_file}>
                  {doc.source_file}
                </p>
                <p className="mt-0.5 text-[10px] opacity-60">
                  {doc.chunk_count} vector chunks
                </p>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
