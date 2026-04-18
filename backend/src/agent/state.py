from typing import Optional, TypedDict
import cadquery as cq
from typing import Optional
from .schema import StructuredPlan


class ExecutionError:
    pass  # imported from executor at runtime to avoid circular


class AgentState(TypedDict):
    user_request: str
    description: str
    plan: str
    plan_obj: Optional[StructuredPlan]
    code: str
    error: Optional[object]   # ExecutionError | None
    fix_history: list[dict]
    attempts: int
    result: Optional[object]  # cq.Shape | cq.Workplane | None
