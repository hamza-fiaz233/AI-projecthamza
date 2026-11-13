import backend.agent  # noqa: F401
from typing import Annotated, Any, Dict, List, Literal, Optional
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage

IntentType = Literal[
    "LIVE_DATA",
    "DOCUMENT",
    "HYBRID",
    "OFF_TOPIC",
    "ADVICE_REQUEST",
]


class AgentState(TypedDict, total=False):
    # Multi-turn conversation messages managed by LangGraph checkpointer
    messages: Annotated[List[BaseMessage], add_messages]

    # Current turn user query & normalized query
    user_query: str
    resolved_query: str

    # Intent classification & extracted entities
    intent: IntentType
    tickers: List[str]
    blocked_reason: Optional[str]

    # Tool execution tracking & bounded loop counter
    tool_calls_made: List[str]
    tool_results: List[Dict[str, Any]]
    retrieved_docs: List[Dict[str, Any]]
    chart_data: Optional[Dict[str, Any]]
    api_timestamps: List[str]

    # Grading & synthesis outputs
    evidence_sufficient: bool
    iteration_count: int
    draft_answer: str
    final_answer: str
    citations: List[Dict[str, Any]]
