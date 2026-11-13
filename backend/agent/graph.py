import backend.agent  # noqa: F401
import json
import re
import time
from typing import Any, Dict, List
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import END, START, StateGraph
from backend.agent.guardrails import guardrail_in, guardrail_out
from backend.agent.memory import get_checkpointer, get_llm, get_session_history, log_chat_turn
from backend.agent.prompts import (
    GRADER_SYSTEM_PROMPT,
    ROUTER_SYSTEM_PROMPT,
    SYNTHESIS_SYSTEM_PROMPT,
    UNDERSTAND_SYSTEM_PROMPT,
)
from backend.agent.state import AgentState
from backend.config import settings
from backend.tools.market_data import get_history, get_quote, get_ratios
from backend.tools.retrieval import retrieve_filings

ALL_TOOLS = [get_quote, get_history, get_ratios, retrieve_filings]
TOOL_MAP = {t.name: t for t in ALL_TOOLS}


def _parse_json_safe(raw: str, fallback: Dict[str, Any]) -> Dict[str, Any]:
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.IGNORECASE)
    try:
        parsed = json.loads(cleaned)
        return parsed if isinstance(parsed, dict) else fallback
    except Exception:
        return fallback


def node_guardrail_in(state: AgentState) -> Dict[str, Any]:
    query = state.get("user_query", "")
    allowed, intent_override, refusal = guardrail_in(query)
    if not allowed:
        return {
            "intent": intent_override or "OFF_TOPIC",
            "blocked_reason": refusal,
            "final_answer": refusal,
            "tool_calls_made": [],
            "tool_results": [],
            "retrieved_docs": [],
            "citations": [],
            "api_timestamps": [],
        }
    return {
        "blocked_reason": None,
        "iteration_count": 0,
        "tool_calls_made": [],
        "tool_results": [],
        "retrieved_docs": [],
        "citations": [],
        "api_timestamps": [],
        "chart_data": None,
    }


def route_after_guardrail_in(state: AgentState) -> str:
    if state.get("blocked_reason"):
        return END
    return "understand"


def node_understand(state: AgentState) -> Dict[str, Any]:
    llm = get_llm(temperature=0.0)
    query = state.get("user_query", "")
    history = state.get("messages", [])[-6:]

    history_text = "\n".join(
        f"{m.type.upper()}: {m.content}" for m in history if getattr(m, "content", None)
    )
    prompt = f"Recent conversation:\n{history_text or 'None'}\n\nCurrent question: {query}"

    resp = llm.invoke([
        SystemMessage(content=UNDERSTAND_SYSTEM_PROMPT),
        HumanMessage(content=prompt),
    ])
    parsed = _parse_json_safe(
        str(resp.content),
        {"resolved_query": query, "tickers": [], "intent": "HYBRID"},
    )

    intent = parsed.get("intent", "HYBRID")
    if intent not in {"LIVE_DATA", "DOCUMENT", "HYBRID"}:
        intent = "HYBRID"

    tickers = [str(t).upper().strip() for t in parsed.get("tickers", []) if t]
    resolved_query = str(parsed.get("resolved_query") or query).strip()

    return {
        "resolved_query": resolved_query,
        "tickers": tickers,
        "intent": intent,
    }


def node_router(state: AgentState) -> Dict[str, Any]:
    llm = get_llm(temperature=0.1).bind_tools(ALL_TOOLS)
    resolved_query = state.get("resolved_query") or state.get("user_query", "")
    tickers = state.get("tickers", [])
    intent = state.get("intent", "HYBRID")
    prior_results = state.get("tool_results", [])

    context_note = (
        f"Detected intent: {intent}. Extracted tickers: {tickers or 'None'}. "
        f"Already collected tool outputs count: {len(prior_results)}."
    )
    if prior_results:
        context_note += f"\nPrevious tool outputs summary: {json.dumps(prior_results, default=str)[:1500]}"

    ai_msg = llm.invoke([
        SystemMessage(content=ROUTER_SYSTEM_PROMPT),
        HumanMessage(content=f"{context_note}\n\nUser request: {resolved_query}"),
    ])
    return {"messages": [ai_msg]}


def route_after_router(state: AgentState) -> str:
    messages = state.get("messages", [])
    last_msg = messages[-1] if messages else None
    if isinstance(last_msg, AIMessage) and getattr(last_msg, "tool_calls", None):
        return "tools"
    return "synthesize"


def node_tools(state: AgentState) -> Dict[str, Any]:
    messages = state.get("messages", [])
    last_msg = messages[-1] if messages else None
    tool_calls = getattr(last_msg, "tool_calls", []) if isinstance(last_msg, AIMessage) else []

    new_tool_messages: List[ToolMessage] = []
    calls_made = list(state.get("tool_calls_made", []))
    results = list(state.get("tool_results", []))
    retrieved = list(state.get("retrieved_docs", []))
    citations = list(state.get("citations", []))
    timestamps = list(state.get("api_timestamps", []))
    chart_data = state.get("chart_data")

    for tc in tool_calls:
        name = tc.get("name", "")
        args = tc.get("args", {}) or {}
        call_id = tc.get("id", name)
        tool_fn = TOOL_MAP.get(name)

        if not tool_fn:
            output = {"error": f"Unknown tool: {name}"}
        else:
            try:
                output = tool_fn.invoke(args)
            except Exception as exc:
                output = {"error": f"Tool '{name}' failed: {str(exc)}"}

        calls_made.append(name)
        results.append({"tool": name, "args": args, "output": output})

        if isinstance(output, dict):
            if output.get("as_of_utc"):
                timestamps.append(output["as_of_utc"])
            if name == "get_history" and output.get("series"):
                chart_data = {
                    "ticker": output.get("ticker"),
                    "period": output.get("period"),
                    "period_return_percent": output.get("period_return_percent"),
                    "series": output.get("series", []),
                }
            if name == "retrieve_filings" and output.get("matches"):
                for m in output["matches"]:
                    retrieved.append(m)
                    citations.append({
                        "citation": m.get("citation"),
                        "source_file": m.get("source_file"),
                        "page": m.get("page"),
                        "section": m.get("section"),
                        "ticker": m.get("ticker"),
                        "snippet": m.get("text", "")[:240],
                    })

        new_tool_messages.append(
            ToolMessage(
                content=json.dumps(output, default=str),
                tool_call_id=call_id,
                name=name,
            )
        )

    return {
        "messages": new_tool_messages,
        "tool_calls_made": calls_made,
        "tool_results": results,
        "retrieved_docs": retrieved,
        "citations": citations,
        "api_timestamps": sorted(set(timestamps)),
        "chart_data": chart_data,
        "iteration_count": state.get("iteration_count", 0) + 1,
    }


def node_grade(state: AgentState) -> Dict[str, Any]:
    iteration = state.get("iteration_count", 0)
    if iteration >= settings.MAX_AGENT_ITERATIONS:
        return {"evidence_sufficient": True}

    llm = get_llm(temperature=0.0)
    query = state.get("resolved_query") or state.get("user_query", "")
    results = state.get("tool_results", [])

    prompt = (
        f"User question: {query}\n"
        f"Collected tool outputs:\n{json.dumps(results, default=str)[:3000]}"
    )
    resp = llm.invoke([
        SystemMessage(content=GRADER_SYSTEM_PROMPT),
        HumanMessage(content=prompt),
    ])
    parsed = _parse_json_safe(str(resp.content), {"sufficient": True, "refined_query": ""})

    sufficient = bool(parsed.get("sufficient", True))
    refined = str(parsed.get("refined_query", "")).strip()
    updates: Dict[str, Any] = {"evidence_sufficient": sufficient}
    if not sufficient and refined:
        updates["resolved_query"] = refined
    return updates


def route_after_grade(state: AgentState) -> str:
    if state.get("evidence_sufficient", True):
        return "synthesize"
    if state.get("iteration_count", 0) >= settings.MAX_AGENT_ITERATIONS:
        return "synthesize"
    return "router"


def node_synthesize(state: AgentState) -> Dict[str, Any]:
    llm = get_llm(temperature=0.1)
    query = state.get("resolved_query") or state.get("user_query", "")
    results = state.get("tool_results", [])

    evidence_text = (
        json.dumps(results, indent=2, default=str)[:6000]
        if results
        else "No tool outputs were returned."
    )
    resp = llm.invoke([
        SystemMessage(content=SYNTHESIS_SYSTEM_PROMPT),
        HumanMessage(content=f"User question: {query}\n\nVerified Tool Evidence:\n{evidence_text}"),
    ])
    return {"draft_answer": str(resp.content)}


def node_guardrail_out(state: AgentState) -> Dict[str, Any]:
    draft = state.get("draft_answer", "")
    results = state.get("tool_results", [])
    retrieved = state.get("retrieved_docs", [])
    final = guardrail_out(draft, results, retrieved)
    return {
        "final_answer": final,
        "messages": [AIMessage(content=final)],
    }


def build_agent_graph():
    workflow = StateGraph(AgentState)

    workflow.add_node("guardrail_in", node_guardrail_in)
    workflow.add_node("understand", node_understand)
    workflow.add_node("router", node_router)
    workflow.add_node("tools", node_tools)
    workflow.add_node("grade", node_grade)
    workflow.add_node("synthesize", node_synthesize)
    workflow.add_node("guardrail_out", node_guardrail_out)

    workflow.add_edge(START, "guardrail_in")
    workflow.add_conditional_edges(
        "guardrail_in",
        route_after_guardrail_in,
        {END: END, "understand": "understand"},
    )
    workflow.add_edge("understand", "router")
    workflow.add_conditional_edges(
        "router",
        route_after_router,
        {"tools": "tools", "synthesize": "synthesize"},
    )
    workflow.add_edge("tools", "grade")
    workflow.add_conditional_edges(
        "grade",
        route_after_grade,
        {"router": "router", "synthesize": "synthesize"},
    )
    workflow.add_edge("synthesize", "guardrail_out")
    workflow.add_edge("guardrail_out", END)

    return workflow.compile(checkpointer=get_checkpointer())


_compiled_graph = None


def get_compiled_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_agent_graph()
    return _compiled_graph


def run_agent(question: str, thread_id: str = "default_session") -> Dict[str, Any]:
    """
    Main public contract called by FastAPI (`api/server.py`) and UI.
    Executes the LangGraph agent workflow and returns structured answer, citations,
    timestamps, tool calls, and optional OHLCV chart data.
    """
    start_time = time.perf_counter()
    graph = get_compiled_graph()

    log_chat_turn(thread_id=thread_id, role="user", content=question)

    config = {"configurable": {"thread_id": thread_id}}
    final_state = graph.invoke(
        {
            "user_query": question,
            "messages": [HumanMessage(content=question)],
        },
        config=config,
    )

    answer = final_state.get("final_answer", "No response generated.")
    intent = final_state.get("intent", "HYBRID")
    tool_calls = final_state.get("tool_calls_made", [])
    citations = final_state.get("citations", [])
    timestamps = final_state.get("api_timestamps", [])
    chart_data = final_state.get("chart_data")
    latency_ms = round((time.perf_counter() - start_time) * 1000, 1)

    log_chat_turn(
        thread_id=thread_id,
        role="assistant",
        content=answer,
        intent=intent,
        tool_calls=tool_calls,
        citations=citations,
    )

    return {
        "thread_id": thread_id,
        "question": question,
        "answer": answer,
        "intent": intent,
        "tickers": final_state.get("tickers", []),
        "tools_called": tool_calls,
        "citations": citations,
        "api_timestamps": timestamps,
        "chart_data": chart_data,
        "latency_ms": latency_ms,
    }
