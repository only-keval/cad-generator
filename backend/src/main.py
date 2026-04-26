import os
import cadquery as cq
from dotenv import load_dotenv
from agent.graph import app
from agent.executor import ExecutionError
from agent.rag import build_retriever

if not load_dotenv():
    print("WARNING: .env not found, assuming env vars are already set.")

build_retriever()  # fast after first run

user_request = input("Enter your 3D model request: ").strip()
if not user_request:
    raise SystemExit("No request provided.")

state = {
    "latest_prompt": user_request,
    "prompt_history": [user_request],
    "mode": "initial",
    "iteration": 1,
    "plan": "",
    "code": "",
    "error": None,
    "fix_history": [],
    "history": [],
    "attempts": 0,
    "result": None,
}

while True:
    print(f"\n--- Iteration {state['iteration']} ({state['mode']}) ---")
    final = app.invoke(state)

    if final["result"] is not None:
        cq.exporters.export(final["result"], "result.stl")
        print("Model exported to result.stl")
    else:
        error: ExecutionError = final["error"]
        print(f"Failed after {final['attempts']} attempts.")
        print(f"Last error - {error.error_type}: {error.message}")

    next_prompt = input("Refine/improve/fix further? (or 'done'): ").strip()
    if next_prompt.lower() in {"done", "quit", "exit"}:
        break
    if not next_prompt:
        print("Empty prompt ignored. Exiting.")
        break

    # Carry forward full in-memory history and latest successful context.
    state = {
        "latest_prompt": next_prompt,
        "prompt_history": list(final.get("prompt_history", [])) + [next_prompt],
        "mode": "refine",
        "iteration": int(final.get("iteration", 1)) + 1,
        "plan": final.get("plan", ""),
        "code": final.get("code", ""),
        "error": None,
        "fix_history": [],
        "history": list(final.get("history", [])),
        "attempts": 0,
        "result": None,
    }

print(f"Session complete. Total history events: {len(state.get('history', []))}")
