import React, { useEffect, useRef, useState } from "react";
import {
  Send,
  Bot,
  User,
  Clock,
  Wrench,
  Sparkles,
  Loader2,
  RotateCcw,
} from "lucide-react";
import { sendChatMessage } from "../services/api";
import StockChart from "./StockChart";
import SourcePanel from "./SourcePanel";

const SAMPLE_PROMPTS = [
  "What is Apple's current stock price and trailing P/E ratio?",
  "Show AAPL 1-month stock price history and period return",
  "What supply chain risks are mentioned in Apple's 10-K?",
  "Compare MSFT and NVDA valuation ratios",
];

export default function ChatWindow({ darkMode, threadId, onNewSession }) {
  const [messages, setMessages] = useState([
    {
      id: "welcome",
      role: "assistant",
      content:
        "Welcome to **FinAI Analyst**! Ask me about live US stock prices, historical price charts, fundamental valuation ratios (P/E, EPS, Market Cap), or insights grounded in your uploaded SEC filings (10-K, 10-Q, transcripts).",
      intent: "SYSTEM",
      tools_called: [],
      citations: [],
      api_timestamps: [],
      chart_data: null,
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const handleReset = () => {
    setMessages([
      {
        id: `welcome-${Date.now()}`,
        role: "assistant",
        content:
          "Started a fresh research session. Ask any question about live stock quotes, historical trends, or uploaded SEC filings.",
        intent: "SYSTEM",
        tools_called: [],
        citations: [],
        api_timestamps: [],
        chart_data: null,
      },
    ]);
    if (onNewSession) onNewSession();
  };

  const submitQuestion = async (questionText) => {
    const trimmed = questionText.trim();
    if (!trimmed || loading) return;

    const userMsg = {
      id: `user-${Date.now()}`,
      role: "user",
      content: trimmed,
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const res = await sendChatMessage(trimmed, threadId);
      const botMsg = {
        id: `bot-${Date.now()}`,
        role: "assistant",
        content: res.answer,
        intent: res.intent,
        tickers: res.tickers || [],
        tools_called: res.tools_called || [],
        citations: res.citations || [],
        api_timestamps: res.api_timestamps || [],
        chart_data: res.chart_data || null,
        latency_ms: res.latency_ms,
      };
      setMessages((prev) => [...prev, botMsg]);
    } catch (err) {
      const detail =
        err?.response?.data?.detail ||
        "Could not reach the FinAI FastAPI server on http://127.0.0.1:8000. Ensure Uvicorn is running.";
      setMessages((prev) => [
        ...prev,
        {
          id: `err-${Date.now()}`,
          role: "assistant",
          content: `**Connection Error:** ${detail}`,
          intent: "ERROR",
          tools_called: [],
          citations: [],
          api_timestamps: [],
          chart_data: null,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    submitQuestion(input);
  };

  const inputThemeClass = darkMode
    ? "border-slate-700 bg-slate-950 text-slate-100 placeholder-slate-500 focus:border-emerald-500"
    : "border-slate-300 bg-white text-slate-900 placeholder-slate-400 focus:border-emerald-600";

  return (
    <div
      className={`flex h-full flex-col rounded-2xl border shadow-sm ${
        darkMode
          ? "border-slate-800 bg-slate-900/60 text-slate-100"
          : "border-slate-200 bg-white text-slate-900"
      }`}
    >
      {/* Top Chat Toolbar */}
      <div
        className={`flex items-center justify-between border-b px-4 py-3 ${
          darkMode ? "border-slate-800" : "border-slate-200"
        }`}
      >
        <div className="flex items-center gap-2">
          <Sparkles size={16} className="text-emerald-500" />
          <span className="text-sm font-semibold">Agentic Equity Research Console</span>
          <span
            className={`hidden rounded-md px-2 py-0.5 font-mono text-[11px] sm:inline ${
              darkMode ? "bg-slate-800 text-slate-400" : "bg-slate-100 text-slate-600"
            }`}
          >
            Session: {threadId}
          </span>
        </div>

        <button
          type="button"
          onClick={handleReset}
          className={`flex items-center gap-1 rounded-lg border px-2.5 py-1 text-xs font-medium transition ${
            darkMode
              ? "border-slate-700 bg-slate-800 text-slate-300 hover:bg-slate-700"
              : "border-slate-300 bg-slate-50 text-slate-700 hover:bg-slate-100"
          }`}
        >
          <RotateCcw size={13} />
          <span>New Thread</span>
        </button>
      </div>

      {/* Quick Starter Prompts */}
      <div
        className={`flex flex-wrap gap-1.5 border-b px-4 py-2.5 ${
          darkMode ? "border-slate-800/80 bg-slate-950/40" : "border-slate-100 bg-slate-50/70"
        }`}
      >
        {SAMPLE_PROMPTS.map((sample) => (
          <button
            key={sample}
            type="button"
            disabled={loading}
            onClick={() => submitQuestion(sample)}
            className={`rounded-full border px-2.5 py-1 text-[11px] transition disabled:opacity-50 ${
              darkMode
                ? "border-slate-700 bg-slate-900 text-slate-300 hover:border-emerald-500/60 hover:text-emerald-400"
                : "border-slate-300 bg-white text-slate-700 hover:border-emerald-600 hover:text-emerald-700"
            }`}
          >
            {sample}
          </button>
        ))}
      </div>

      {/* Message Stream */}
      <div className="flex-1 space-y-4 overflow-y-auto p-4">
        {messages.map((msg) => {
          const isUser = msg.role === "user";
          return (
            <div
              key={msg.id}
              className={`flex items-start gap-3 ${isUser ? "flex-row-reverse" : ""}`}
            >
              <div
                className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${
                  isUser
                    ? "bg-emerald-600 text-white"
                    : darkMode
                    ? "bg-slate-800 text-emerald-400"
                    : "bg-slate-200 text-emerald-700"
                }`}
              >
                {isUser ? <User size={16} /> : <Bot size={16} />}
              </div>

              <div
                className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                  isUser
                    ? "bg-emerald-600 text-white"
                    : darkMode
                    ? "border border-slate-800 bg-slate-950/90 text-slate-100"
                    : "border border-slate-200 bg-slate-50 text-slate-900"
                }`}
              >
                {/* Assistant Telemetry Header */}
                {!isUser && msg.intent && msg.intent !== "SYSTEM" && (
                  <div className="mb-2 flex flex-wrap items-center gap-1.5 text-[11px]">
                    <span className="rounded bg-emerald-500/15 px-2 py-0.5 font-semibold text-emerald-400">
                      {msg.intent}
                    </span>

                    {msg.tools_called?.map((tool, i) => (
                      <span
                        key={`${tool}-${i}`}
                        className={`flex items-center gap-1 rounded px-2 py-0.5 font-mono ${
                          darkMode
                            ? "bg-slate-800 text-sky-300"
                            : "bg-sky-100 text-sky-800"
                        }`}
                      >
                        <Wrench size={10} />
                        {tool}
                      </span>
                    ))}

                    {msg.latency_ms && (
                      <span className="opacity-60">{(msg.latency_ms / 1000).toFixed(1)}s</span>
                    )}
                  </div>
                )}

                {/* Answer Body */}
                <div className="whitespace-pre-wrap break-words">{msg.content}</div>

                {/* Live API UTC Timestamps */}
                {!isUser && msg.api_timestamps?.length > 0 && (
                  <div className="mt-2.5 flex flex-wrap items-center gap-1.5 text-[11px] opacity-75">
                    <Clock size={12} className="text-emerald-400" />
                    <span>Live API UTC:</span>
                    {msg.api_timestamps.map((ts) => (
                      <code
                        key={ts}
                        className={`rounded px-1.5 py-0.5 font-mono text-[10px] ${
                          darkMode ? "bg-slate-800" : "bg-slate-200"
                        }`}
                      >
                        {ts}
                      </code>
                    ))}
                  </div>
                )}

                {/* Interactive Stock Price Chart */}
                {!isUser && msg.chart_data && (
                  <StockChart chartData={msg.chart_data} darkMode={darkMode} />
                )}

                {/* Expandable Filing Source Citations */}
                {!isUser && msg.citations?.length > 0 && (
                  <SourcePanel citations={msg.citations} darkMode={darkMode} />
                )}
              </div>
            </div>
          );
        })}

        {loading && (
          <div className="flex items-center gap-2.5 text-xs opacity-80">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-800 text-emerald-400">
              <Loader2 size={16} className="animate-spin" />
            </div>
            <span>
              LangGraph agent is routing tools, verifying figures, and checking guardrails...
            </span>
          </div>
)}
{/* Input Form */}
      <form onSubmit={handleSubmit} className={"border-t p-3 " + (darkMode ? "border-slate-800" : "border-slate-200")}>
        <div className="flex items-center gap-2">
          <input type="text" value={input} onChange={(e) => setInput(e.target.value)} placeholder="Ask about AAPL price, 1mo trend, P/E ratio, or 10-K risk factors..." disabled={loading} className={"flex-1 rounded-xl border px-3.5 py-2.5 text-sm outline-none transition " + inputThemeClass} />
          <button type="submit" disabled={loading || !input.trim()} className="flex items-center gap-1.5 rounded-xl bg-emerald-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-emerald-500 disabled:opacity-50">
            <Send size={15} />
            <span>Ask</span>
          </button>
        </div>
      </form>
      </div>
    </div>
  );
}
