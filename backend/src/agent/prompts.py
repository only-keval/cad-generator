from typing import Optional


def plan_prompt(user_request: str) -> str:
    return (
        f"Design a precise 3D model for: {user_request}.\n"
        f"Step 1: Describe the object geometrically.\n"
        f"- Break the object into simple primitives (box, cylinder, sphere, etc.).\n"
        f"- For each primitive, specify approximate dimensions in millimeters.\n"
        f"- Specify the spatial relationship between primitives (position, alignment, offsets).\n"
        f"- Describe the overall shape clearly enough for a CAD engineer to understand.\n\n"
        f"Step 2: Provide a step-by-step plan to build the object in CadQuery.\n"
        f"- Each step should correspond to creating or modifying a primitive using CadQuery operations (extrude, fillet, cut, union, etc.).\n"
        f"- Include information on relative positions and dimensions in each step.\n"
        f"- Avoid giving any actual code.\n"
        f"- Keep steps detailed enough so a CadQuery script can be generated directly from them.\n"
        f"- Avoid using chamfers unnecessarily unless specified.\n"
    )


def codegen_prompt(plan: str, api_context: str) -> str:
    return (
        f"You are an expert CadQuery programmer. You have access to the full CadQuery 2 API.\n"
        f"CONTEXT: <API REFERENCE>\n"
        f"{api_context}\n"
        f"<END API REFERENCE>\n\n"
        f"PLAN:\n"
        f"{plan}\n\n"
        f"Based on the above plan, write Python code that constructs the described 3D model using CadQuery 2.\n"
        f"STRICT RULES:\n"
        f"- Use CadQuery ONLY through the existing variable named 'cq' which is already available in the environment.\n"
        f"- You can use safe python builtin functions and math functions via 'math'.\n"
        f"- Use only functions and classes that actually exist in cadquery from the API reference. Do NOT hallucinate anything.\n"
        f"- Do NOT import anything. No 'import cadquery', No 'import math', no imports of any kind.\n"
        f"- Define a function build() with no arguments.\n"
        f"- build() must return the final CadQuery Workplane or Shape.\n"
        f"- Define ONLY the build() function, no additional code outside of it.\n"
        f"- Do NOT export files.\n"
        f"- Do NOT include comments.\n"
        f"- Output ONLY pure Python code, NO markdown formatting, NO surrounding text.\n"
    )


def diagnose_prompt(plan: str, api_context: str, numbered_code: str, error_text: str, fix_history: list[dict]) -> str:
    history_text = ""
    if fix_history:
        lines = [f"{i+1}. Error: {h['error']}\n   Fix attempted: {h['summary']}" for i, h in enumerate(fix_history)]
        history_text = "\nPrevious fixes:\n" + "\n".join(lines)

    return (
        f"You are an expert CadQuery programmer. You have access to the full CadQuery 2 API.\n"
        f"CONTEXT: <API REFERENCE>\n"
        f"{api_context}\n"
        f"<END API REFERENCE>\n\n"
        f"<PLAN>\n"
        f"{plan}\n"
        f"<END PLAN>\n\n"
        f"The following CadQuery code failed:\n\n"
        f"{numbered_code}\n\n"
        f"Error:\n{error_text}\n"
        f"{history_text}\n\n"
        f"STRICT RULES:\n"
        f"- Use only functions and classes that actually exist in cadquery from the API reference.\n"
        f"- If the error is an import, know that cq and math are already in scope — nothing else is allowed.\n"
        f"- If statements span multiple lines, note all affected lines.\n"
        f"- Explain the cause and which lines need modification.\n"
        f"- Do NOT propose code yet, just provide a clear diagnosis and fix plan.\n"
        f"- Output only plain text.\n"
    )


def regen_prompt(numbered_code: str, diagnosis: str) -> str:
    return (
        f"You have the numbered code:\n\n{numbered_code}\n\n"
        f"and the diagnosis/fix plan:\n\n{diagnosis}\n\n"
        f"Regenerate the FULL corrected code and provide a brief summary of the fix.\n"
        f"STRICT RULES:\n"
        f"- Use CadQuery ONLY through the existing variable named 'cq'.\n"
        f"- You can use safe python builtin functions and math functions via 'math'.\n"
        f"- Do NOT import anything.\n"
        f"- Define a function build() with no arguments that returns the final CadQuery Workplane or Shape.\n"
        f"- Define ONLY the build() function, no additional code outside of it.\n"
        f"- Do NOT export files.\n"
        f"- Do NOT include comments.\n"
        f"- Output ONLY pure Python code. Remove the line number prefixes.\n"
        f"- Provide a concise summary (1-2 sentences) of the fix in the 'fix_summary' field.\n"
    )
