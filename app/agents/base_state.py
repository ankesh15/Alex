from typing import Annotated, TypedDict, Any, Dict, List
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class BaseAgentState(TypedDict):
    """
    Base Agent State inherited by all module-specific graphs.
    Enforces DRY principle for state definitions.
    """
    messages: Annotated[List[BaseMessage], add_messages]
    status: str
    error: str | None
    metadata: Dict[str, Any]
