from typing import Optional, TypedDict
from .executor import ExecutionError
import cadquery as cq


class AgentState(TypedDict):
    latest_prompt: str
    prompt_history: list[str]
    mode: str
    iteration: int
    plan: str
    code: str
    error: Optional[ExecutionError]
    fix_history: list[dict]
    attempts: int
    result: Optional[object]  # cq.Shape | cq.Workplane | None
