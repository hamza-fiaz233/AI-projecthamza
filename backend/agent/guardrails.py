import json
import re
from typing import Any, Dict, List, Tuple

DISCLAIMER_TEXT = (
    "\n\n---\n*Disclaimer: FinAI Analyst is an educational research prototype. "
    "All outputs are informational and do not constitute financial, investment, or legal advice.*"
)

# Patterns for prompt injection attempts
INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"disregard\s+(all\s+)?prior\s+instructions",
    r"forget\s+your\s+rules",
    r"system\s+prompt",
    r"you\s+are\s+now\s+dan",
    r"bypass\s+guardrail",
]

# Patterns for personalized investment advice requests
ADVICE_PATTERNS = [
    r"\bshould\s+i\s+(buy|sell|short|hold|invest\s+in)\b",
    r"\bcan\s+you\s+recommend\s+(a\s+)?stock(s)?\s+to\s+buy\b",
    r"\bwhat\s+stock(s)?\s+should\s+i\s+(buy|invest)\b",
    r"\btell\s+me\s+what\s+to\s+(buy|sell|invest)\b",
    r"\bguarantee(d)?\s+return",
]

# Finance domain keywords to reject clearly off-topic prompts
FINANCE_KEYWORDS = {
    "stock", "stocks", "share", "shares", "price", "prices", "market", "ticker",
    "p/e", "pe", "eps", "ratio", "ratios", "valuation", "revenue", "margin",
    "margins", "earnings", "10-k", "10k", "10-q", "10q", "8-k", "sec", "filing",
    "filings", "transcript", "risk", "risks", "guidance", "dividend", "yield",
    "cap", "volume", "history", "chart", "trend", "quarter", "fiscal", "balance",
    "sheet", "income", "cash", "flow", "debt", "equity", "nyse", "nasdaq",
    "company", "finance", "financial", "analyst", "etf", "index", "s&p",
    "apple", "aapl", "microsoft", "msft", "nvidia", "nvda", "tesla", "tsla",
    "amazon", "amzn", "google", "googl", "alphabet", "meta", "netflix", "nflx",
}


def guardrail_in(query: str) -> Tuple[bool, str, str]:
    """
    Validate incoming user query.
    Returns (allowed: bool, intent_override: str, refusal_message: str).
    """
    if not query or not query.strip():
        return False, "OFF_TOPIC", "Please enter a financial question about a stock or SEC filing."

    text = query.strip()
    lower = text.lower()

    # 1. Check for prompt injection
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, lower):
            return (
                False,
                "OFF_TOPIC",
                "Request blocked by security policy: prompt-injection or instruction-override attempts are not permitted.",
            )

    # 2. Check for personalized buy/sell advice requests
    for pattern in ADVICE_PATTERNS:
        if re.search(pattern, lower):
            return (
                False,
                "ADVICE_REQUEST",
                (
                    "I cannot provide personalized buy, sell, or investment recommendations. "
                    "However, I can share factual market data, valuation ratios (such as P/E and EPS), "
                    "or risk factors disclosed in a company's SEC filings. Which company would you like to analyze?"
                    + DISCLAIMER_TEXT
                ),
            )

    # 3. Check finance domain relevance (allow short follow-ups like "and its P/E?" or uppercase tickers)
    tokens = set(re.findall(r"[a-z0-9&.-]+", lower))
    has_ticker_token = bool(re.search(r"\b[A-Z]{2,5}\b", text))
    is_short_followup = len(tokens) <= 6 and any(
        w in tokens for w in {"it", "its", "their", "they", "that", "more", "why", "compare", "history"}
    )

    if not (tokens & FINANCE_KEYWORDS) and not has_ticker_token and not is_short_followup:
        return (
            False,
            "OFF_TOPIC",
            (
                "FinAI Analyst only answers questions related to US equities, live market data, "
                "financial ratios, and SEC filings (10-K, 10-Q, transcripts). "
                "Please ask a stock or financial analysis question."
            ),
        )

    return True, "", ""


def guardrail_out(
    draft: str,
    tool_results: List[Dict[str, Any]],
    retrieved_docs: List[Dict[str, Any]],
) -> str:
    """
    Verify output grounding:
    1. Cross-check numeric figures against tool outputs and flag unverified numbers.
    2. Ensure citations from retrieved_docs are included when document passages were used.
    3. Append mandatory educational disclaimer.
    """
    if not draft or not draft.strip():
        return "I could not generate a grounded answer from the available tools." + DISCLAIMER_TEXT

    output = draft.strip()

    # Serialize all tool outputs to check numeric provenance
    evidence_blob = json.dumps(tool_results, default=str)
    evidence_numbers = set(re.findall(r"\d+(?:\.\d+)?", evidence_blob))

    # Extract multi-digit/decimal figures in draft (ignore single-digit list bullets or years like 2024-2026)
    draft_numbers = re.findall(r"\b\d+\.\d+\b|\b\d{2,}\b", output)
    unverified = [
        num for num in draft_numbers
        if num not in evidence_numbers and num not in {"2023", "2024", "2025", "2026", "10", "52"}
    ]

    if unverified and tool_results:
        unique_unverified = sorted(set(unverified))[:5]
        output += (
            f"\n\n*Verification Note: Figures {', '.join(unique_unverified)} were not directly matched "
            "as raw strings in tool outputs; please verify against the cited timestamps and filings.*"
        )

    # Ensure at least one [Source: ...] citation appears if retrieved_docs were used
    if retrieved_docs and "[Source:" not in output:
        citations = sorted({d.get("citation", "") for d in retrieved_docs if d.get("citation")})
        if citations:
            output += "\n\n**Sources:** " + ", ".join(citations)

    # Append disclaimer if not already attached
    if "Disclaimer: FinAI Analyst" not in output:
        output += DISCLAIMER_TEXT

    return output
