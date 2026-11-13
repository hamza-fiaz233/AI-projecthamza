import React, { useEffect, useState } from "react";
import {
  TrendingUp,
  Sun,
  Moon,
  ShieldAlert,
  Activity,
} from "lucide-react";
import ChatWindow from "./components/ChatWindow";
import PdfUploader from "./components/PdfUploader";
import { checkHealth } from "./services/api";

function makeThreadId() {
  return `session_${Math.random().toString(36).substring(2, 9)}`;
}

export default function App() {
  const [darkMode, setDarkMode] = useState(true);
  const [threadId, setThreadId] = useState(() => makeThreadId());
  const [backendStatus, setBackendStatus] = useState({
    online: false,
    model: "",
  });

  useEffect(() => {
    let active = true;
    const pingBackend = async () => {
      try {
        const res = await checkHealth();
        if (active && res.status === "ok") {
          setBackendStatus({ online: true, model: res.model || "LLM Ready" });
        }
      } catch {
        if (active) {
          setBackendStatus({ online: false, model: "" });
        }
      }
    };
    pingBackend();
    const timer = setInterval(pingBackend, 15000);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, []);

  return (
    <div
      className={`min-h-screen transition-colors ${
        darkMode ? "bg-slate-950 text-slate-100" : "bg-slate-100 text-slate-900"
      }`}
    >
      {/* Top Navigation Bar */}
      <header
        className={`border-b px-4 py-3 sm:px-6 ${
          darkMode
            ? "border-slate-800 bg-slate-900/90"
            : "border-slate-200 bg-white"
        }`}
      >
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-emerald-600 text-white shadow-sm">
              <TrendingUp size={20} />
            </div>
            <div>
              <h1 className="text-base font-bold tracking-tight sm:text-lg">
                FinAI Analyst
              </h1>
              <p className="text-[11px] opacity-70">
                Agentic RAG & Live Equity Research Workstation
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* Backend Connection Pill */}
            <div
              className={`flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium ${
                backendStatus.online
                  ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-400"
                  : "border-rose-500/30 bg-rose-500/10 text-rose-400"
              }`}
            >
              <Activity size={13} />
              <span>
                {backendStatus.online
                  ? `API Online (${backendStatus.model})`
                  : "API Offline (Start Uvicorn)"}
              </span>
            </div>

            {/* Dark / Light Theme Toggle */}
            <button
              type="button"
              onClick={() => setDarkMode((prev) => !prev)}
              aria-label="Toggle color theme"
              className={`rounded-xl border p-2 transition ${
                darkMode
                  ? "border-slate-700 bg-slate-800 text-amber-300 hover:bg-slate-700"
                  : "border-slate-300 bg-slate-100 text-slate-700 hover:bg-slate-200"
              }`}
            >
              {darkMode ? <Sun size={16} /> : <Moon size={16} />}
            </button>
          </div>
        </div>
      </header>

      {/* Persistent Educational Disclaimer Banner */}
      <div
        className={`border-b px-4 py-2 text-xs ${
          darkMode
            ? "border-amber-500/20 bg-amber-500/10 text-amber-200"
            : "border-amber-300 bg-amber-50 text-amber-900"
        }`}
      >
        <div className="mx-auto flex max-w-7xl items-center gap-2">
          <ShieldAlert size={15} className="shrink-0 text-amber-400" />
          <span>
            <strong>Non-Advice Notice:</strong> FinAI Analyst provides factual market
            data and SEC filing citations for educational research only—never
            personalized buy, sell, or investment recommendations.
          </span>
        </div>
      </div>

      {/* Main Two-Column Workstation */}
      <main className="mx-auto grid max-w-7xl grid-cols-1 gap-4 p-4 sm:p-6 lg:grid-cols-12">
        <aside className="lg:col-span-4 xl:col-span-3">
          <PdfUploader darkMode={darkMode} />
        </aside>

        <section className="h-[calc(100vh-11.5rem)] min-h-[540px] lg:col-span-8 xl:col-span-9">
          <ChatWindow
            darkMode={darkMode}
            threadId={threadId}
            onNewSession={() => setThreadId(makeThreadId())}
          />
        </section>
      </main>
    </div>
  );
}
