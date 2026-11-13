import React, { useState } from "react";
import { FileText, ChevronDown, ChevronUp, Clock, Wrench } from "lucide-react";

export default function SourcePanel({
  citations = [],
  apiTimestamps = [],
  toolsCalled = [],
  latencyMs = null,
  darkMode = true,
}) {
  const [expanded, setExpanded] = useState(false);

  const hasCitations = Array.isArray(citations) && citations.length > 0;
  const hasTimestamps = Array.isArray(apiTimestamps) && apiTimestamps.length > 0;
  const hasTools = Array.isArray(toolsCalled) && toolsCalled.length > 0;

  if (!hasCitations && !hasTimestamps && !hasTools) {
    return null;
  }

  return (
    <div
      className={`mt-3 rounded-xl border text-xs transition-colors ${
        darkMode
          ? "border-slate-700/80 bg-slate-900/60 text-slate-300"
          : "border-slate-200 bg-slate-50 text-slate-700"
      }`}
    >
      {/* Metadata & Toggle Bar */}
      <div className="flex flex-wrap items-center justify-between gap-2 px-3 py-2">
        <div className="flex flex-wrap items-center gap-2">
          {hasTools && (
            <span
              className={`inline-flex items-center gap-1 rounded-md px-2 py-0.5 font-mono text-[11px] ${
                darkMode
                  ? "bg-indigo-500/15 text-indigo-300"
                  : "bg-indigo-100 text-indigo-700"
              }`}
            >
              <Wrench size={11} />
              {toolsCalled.join(", ")}
            </span>
          )}

          {hasTimestamps && (
            <span
              className={`inline-flex items-center gap-1 rounded-md px-2 py-0.5 font-mono text-[11px] ${
                darkMode
                  ? "bg-emerald-500/15 text-emerald-300"
                  : "bg-emerald-100 text-emerald-700"
              }`}
            >
              <Clock size={11} />
              UTC: {apiTimestamps.replace("T", " ").slice(0, 19)}Z
            </span>
          )}

          {latencyMs !== null && (
            <span className="text-[11px] opacity-70">{latencyMs} ms</span>
          )}
        </div>

        {hasCitations && (
          <button
            type="button"
            onClick={() => setExpanded((prev) => !prev)}
            className={`inline-flex items-center gap-1 rounded-md px-2 py-1 font-medium transition ${
              darkMode
                ? "bg-slate-800 text-amber-300 hover:bg-slate-700"
                : "bg-amber-100 text-amber-800 hover:bg-amber-200"
            }`}
          >
            <FileText size={12} />
            <span>
              {citations.length} Source {citations.length === 1 ? "Citation" : "Citations"}
            </span>
            {expanded ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
          </button>
        )}
      </div>

      {/* Expandable Citation Cards */}
      {hasCitations && expanded && (
        <div
          className={`space-y-2 border-t px-3 py-2.5 ${
            darkMode ? "border-slate-800" : "border-slate-200"
          }`}
        >
          {citations.map((item, idx) => (
            <div
              key={`${item.source_file}-${item.page}-${idx}`}
              className={`rounded-lg border p-2.5 ${
                darkMode
                  ? "border-slate-700/70 bg-slate-950/70"
                  : "border-slate-200 bg-white"
              }`}
            >
              <div className="mb-1 flex flex-wrap items-center justify-between gap-1">
                <span className="font-semibold text-amber-400">
                  {item.citation || `[Source: ${item.source_file}, p.${item.page}]`}
                </span>
                <span
                  className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${
                    darkMode
                      ? "bg-slate-800 text-slate-300"
                      : "bg-slate-100 text-slate-600"
                  }`}
                >
                  {item.ticker ? `${item.ticker} • ` : ""}
                  {item.section || "General"}
                </span>
              </div>
              {item.snippet && (
                <p className="line-clamp-3 leading-relaxed opacity-85">
                  “{item.snippet}...”
                </p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
