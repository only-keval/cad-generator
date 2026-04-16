from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field

from .state import AgentState
from .executor import CadqueryExecutor, ExecutionError
from .prompts import plan_prompt, codegen_prompt, diagnose_prompt, regen_prompt
from .llm import llm, llm_structured
from .rag import retrieve, retrieve_for_plan, retrieve_for_error


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

MAX_ATTEMPTS = 5
executor = CadqueryExecutor()


class RegenResponse(BaseModel):
    code: str = Field(description="The full corrected Python code")
    fix_summary: str = Field(description="1-2 sentence description of the fix")


# ---------------------------------------------------------------------------
# Code post-processing
# ---------------------------------------------------------------------------

def _clean(code: str) -> str:
    lines = code.splitlines()
    if code.startswith("```") and code.endswith("```"):
        lines = lines[1:-1]
    lines = [l for l in lines if not l.strip().startswith("import ")]
    return "\n".join(lines)


def _number(code: str) -> str:
    return "\n".join(f"{i+1:04d}| {l}" for i, l in enumerate(code.splitlines()))


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------

def node_plan(state: AgentState) -> dict:
    print("Planning model...")
    plan = llm(plan_prompt(state["user_request"]))
    print(f"Plan:\n{plan}\n")
    return {"plan": plan}


def node_codegen(state: AgentState) -> dict:
    print("Generating code...")
    docs = retrieve_for_plan(state["plan"])
    # print(f"Retrieved docs:\n{docs}\n")
    code = _clean(llm(codegen_prompt(state["plan"], docs)))
    print(f"Generated code:\n{code}\n")
    return {"code": code}


def node_execute(state: AgentState) -> dict:
    attempt = state.get("attempts", 0)
    print(f"Executing (attempt {attempt + 1})...")
    result, error = executor.run(state["code"])
    if error:
        print(f"Error: {error.error_type}: {error.message}\n")
    return {"result": result, "error": error, "attempts": attempt + 1}


def node_fix(state: AgentState) -> dict:
    print("Diagnosing error...")
    error: ExecutionError = state["error"]
    error_text = f"Error on line {error.line}:\n{error.error_type}: {error.message}\n{error.traceback}"

    docs = retrieve_for_error(state["code"], error.error_type, error.message)
    # print(f"Retrieved docs:\n{docs}\n")

    diagnosis = llm(
        diagnose_prompt(
            plan=state["plan"],
            api_context=docs,
            numbered_code=_number(state["code"]),
            error_text=error_text,
            fix_history=state["fix_history"],
        )
    )
    print(f"Diagnosis:\n{diagnosis}\n")

    print("Regenerating code...")
    docs = retrieve_for_plan(diagnosis)
    regen = llm_structured(regen_prompt(state["plan"], docs, _number(state["code"]), diagnosis), RegenResponse)
    fixed_code = _clean(regen.code)
    print(f"Fixed code:\n{fixed_code}\n")

    history = state.get("fix_history", []) + [
        {"error": f"{error.error_type}: {error.message}", "summary": regen.fix_summary}
    ]
    return {"code": fixed_code, "fix_history": history}


# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------

def _route(state: AgentState) -> str:
    if state["error"] is None:
        return "done"
    if state["attempts"] >= MAX_ATTEMPTS:
        return "give_up"
    return "fix"


# ---------------------------------------------------------------------------
# Graph
# ---------------------------------------------------------------------------

def build_graph():
    g = StateGraph(AgentState)

    g.add_node("plan",    node_plan)
    g.add_node("codegen", node_codegen)
    g.add_node("execute", node_execute)
    g.add_node("fix",     node_fix)

    g.set_entry_point("plan")
    g.add_edge("plan",    "codegen")
    g.add_edge("codegen", "execute")
    g.add_edge("fix",     "execute")

    g.add_conditional_edges("execute", _route, {
        "done":     END,
        "give_up":  END,
        "fix":      "fix",
    })

    return g.compile()


app = build_graph()
