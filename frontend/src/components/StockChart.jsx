import React from "react";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";
import { TrendingUp, TrendingDown } from "lucide-react";

export default function StockChart({ chartData, darkMode }) {
  if (!chartData || !Array.isArray(chartData.series) || chartData.series.length === 0) {
    return null;
  }

  const { ticker, period, period_return_percent, series } = chartData;
  const isPositive = (period_return_percent ?? 0) >= 0;
  const strokeColor = isPositive ? "#10b981" : "#ef4444";

  return (
    <div
      className={`mt-3 rounded-xl border p-4 transition-colors ${
        darkMode
          ? "border-slate-700 bg-slate-900/80 text-slate-100"
          : "border-slate-200 bg-slate-50 text-slate-900"
      }`}
    >
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="text-sm font-bold tracking-wide">{ticker}</span>
          <span
            className={`rounded-md px-2 py-0.5 text-xs font-medium uppercase ${
              darkMode ? "bg-slate-800 text-slate-300" : "bg-slate-200 text-slate-700"
            }`}
          >
            {period}
          </span>
        </div>

        {period_return_percent !== undefined && period_return_percent !== null && (
          <div
            className={`flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold ${
              isPositive
                ? "bg-emerald-500/15 text-emerald-400"
                : "bg-rose-500/15 text-rose-400"
            }`}
          >
            {isPositive ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
            <span>
              {isPositive ? "+" : ""}
              {period_return_percent}%
            </span>
          </div>
        )}
      </div>

      <div className="h-52 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={series} margin={{ top: 6, right: 12, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id={`grad-${ticker}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={strokeColor} stopOpacity={0.35} />
                <stop offset="95%" stopColor={strokeColor} stopOpacity={0.0} />
              </linearGradient>
            </defs>
            <CartesianGrid
              strokeDasharray="3 3"
              stroke={darkMode ? "#1e293b" : "#e2e8f0"}
            />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 11, fill: darkMode ? "#94a3b8" : "#64748b" }}
              tickLine={false}
              axisLine={false}
              minTickGap={20}
            />
            <YAxis
              domain={["auto", "auto"]}
              tick={{ fontSize: 11, fill: darkMode ? "#94a3b8" : "#64748b" }}
              tickLine={false}
              axisLine={false}
              width={52}
              tickFormatter={(val) => `$${val}`}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: darkMode ? "#0f172a" : "#ffffff",
                borderColor: darkMode ? "#334155" : "#cbd5e1",
                borderRadius: "8px",
                fontSize: "12px",
              }}
              formatter={(value) => [`$${Number(value).toFixed(2)}`, "Close"]}
            />
            <Area
              type="monotone"
              dataKey="close"
              stroke={strokeColor}
              strokeWidth={2}
              fillOpacity={1}
              fill={`url(#grad-${ticker})`}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
