from typing import Optional, TypedDict
import cadquery as cq


class ExecutionError:
    pass  # imported from executor at runtime to avoid circular


class AgentState(TypedDict):
    user_request: str
    plan: str
    code: str
    error: Optional[object]   # ExecutionError | None
    fix_history: list[dict]
    attempts: int
    result: Optional[object]  # cq.Shape | cq.Workplane | None
