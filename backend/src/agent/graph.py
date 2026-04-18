from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field

from .state import AgentState
from .executor import CadqueryExecutor, ExecutionError
from .prompts import description_prompt, plan_prompt, codegen_prompt, diagnose_prompt, regen_prompt
from .llm import llm, llm_structured
from .rag import retrieve, retrieve_for_plan, retrieve_for_error
from .schema import StructuredPlan
import json


MAX_ATTEMPTS = 5
executor = CadqueryExecutor()


class RegenResponse(BaseModel):
    code: str = Field(description="The full corrected Python code")
    fix_summary: str = Field(description="1-2 sentence description of the fix")


def _validate_references(plan: StructuredPlan):
    ids = {p.id for p in plan.primitives}
    for c in plan.constraints:
        if c.target not in ids:
            raise ValueError(f"Invalid target: {c.target}")
        if c.reference and c.reference not in ids:
            raise ValueError(f"Invalid reference: {c.reference}")


def _clean(code: str) -> str:
    code = code.strip()
    if code.startswith("```"):
        lines = code.splitlines()
        lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        code = "\n".join(lines)

    lines = [l for l in code.splitlines() if not l.strip().startswith("import ")]
    return "\n".join(lines)

def _number(code: str) -> str:
    return "\n".join(f"{i+1:04d}| {l}" for i, l in enumerate(code.splitlines()))


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------

def node_describe(state: AgentState) -> dict:
    print("Generating design brief...")
    description = llm(description_prompt(state["user_request"])).strip()
    print(f"Description:\n{description}\n")
    return {"description": description}


def node_plan(state: AgentState) -> dict:
    print("Planning model...")

    for _ in range(3):  # retry on bad structure
        try:
            plan_obj = llm_structured(
                plan_prompt(state["description"]),
                StructuredPlan
            )
            _validate_references(plan_obj)
            break
        except Exception as e:
            print(f"[plan retry] {e}")
    else:
        raise RuntimeError("Failed to generate valid structured plan")

    plan_json = plan_obj.model_dump_json()
    print(f"Plan:\n{plan_json}\n")

    return {
        "plan": plan_json,
        "plan_obj": plan_obj  # keep structured version too
    }

def node_codegen(state: AgentState) -> dict:
    print("Generating code...")
    plan_obj = state["plan_obj"]
    # extract useful terms from structured plan
    terms = [p.type for p in plan_obj.primitives]
    docs = retrieve_for_plan(" ".join(terms))# print(f"Retrieved docs:\n{docs}\n")
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

    error_text = (
        f"Error on line {error.line}:\n"
        f"{error.error_type}: {error.message}\n"
        f"{error.traceback}"
    )

    # 🔹 Better retrieval: error-specific + plan context
    error_docs = retrieve_for_error(state["code"], error.error_type, error.message)
    plan_docs = retrieve_for_plan(state["plan"])
    docs = error_docs + "\n\n---\n\n" + plan_docs

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

    # 🔹 Use SAME combined docs for regeneration (not diagnosis text)
    regen = llm_structured(
        regen_prompt(
            state["plan"],
            docs,
            _number(state["code"]),
            diagnosis
        ),
        RegenResponse
    )

    fixed_code = _clean(regen.code)
    print(f"Fixed code:\n{fixed_code}\n")

    # 🔹 Prevent stagnation (same code again)
    if fixed_code.strip() == state["code"].strip():
        print("[fix] No change in code, stopping retries.")
        return {
            "code": fixed_code,
            "fix_history": state.get("fix_history", []),
            "attempts": 999  # force exit
        }

    history = state.get("fix_history", []) + [
        {
            "error": f"{error.error_type}: {error.message}",
            "summary": regen.fix_summary
        }
    ]

    return {
        "code": fixed_code,
        "fix_history": history
    }


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

    g.add_node("describe", node_describe)
    g.add_node("plan",    node_plan)
    g.add_node("codegen", node_codegen)
    g.add_node("execute", node_execute)
    g.add_node("fix",     node_fix)

    g.set_entry_point("describe")
    g.add_edge("describe", "plan")
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
