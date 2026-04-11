import os
import cadquery as cq
from dotenv import load_dotenv
from agent.graph import app
from agent.executor import ExecutionError

if not load_dotenv():
    print("WARNING: .env not found, assuming env vars are already set.")

api_context = open("data/cadquery_api_reference.txt", encoding="utf-8").read()
user_request = input("Enter your 3D model request: ")

final = app.invoke({
    "user_request": user_request,
    "api_context":  api_context,
    "plan":         "",
    "code":         "",
    "error":        None,
    "fix_history":  [],
    "attempts":     0,
    "result":       None,
})

if final["result"] is not None:
    cq.exporters.export(final["result"], "result.stl")
    print("Model exported to result.stl")
else:
    error: ExecutionError = final["error"]
    print(f"Failed after {final['attempts']} attempts.")
    print(f"Last error — {error.error_type}: {error.message}")
