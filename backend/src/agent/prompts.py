from typing import Optional


def plan_prompt(user_request: str) -> str:
    return (
        f"Design a precise 3D model for: {user_request}.\n\n"

        f"Use CadQuery coordinate system conventions:\n"
        f"- +Z is up (vertical direction)\n"
        f"- XY plane is the ground/base plane\n"
        f"- +X is right, +Y is forward\n"
        f"- Always use axis-based directions (e.g., '+Z', '-X'), avoid ambiguous terms like 'above' unless tied to axes\n\n"

        f"Step 1: Describe the object geometrically.\n"
        f"- Break the object into simple primitives (box, cylinder, sphere, etc.).\n"
        f"- Define a base primitive anchored at origin (0,0,0).\n"
        f"- Specify approximate dimensions in millimeters.\n"
        f"- Describe orientations using axes (e.g., 'cylinder aligned along Z-axis').\n"
        f"- Specify spatial relationships using coordinates, offsets, or references to faces/edges.\n"
        f"- Define positions relative to the base primitive whenever possible.\n"
        f"- Keep the model simple and avoid unnecessary complexity.\n\n"

        f"Step 2: Provide a step-by-step plan to build the object in CadQuery.\n"
        f"- Build from bottom to top along +Z.\n"
        f"- Each step should correspond to a CadQuery operation (extrude, cut, union, etc.).\n"
        f"- Specify positions and orientations explicitly using axes.\n"
        f"- Avoid chamfers and fillets unless necessary.\n\n"

        f"Step 3: Validate the geometry.\n"
        f"- Ensure all intended vertical structures extend along +Z.\n"
        f"- Ensure no unintended parts go below the XY plane.\n"
        f"- Confirm all orientations and alignments are consistent.\n"
    )


def codegen_prompt(plan: str, api_context: str) -> str:
    return (
        f"You are an expert CadQuery programmer. You have access to the full CadQuery 2 API.\n"
        f"<CONTEXT>\n"
        f"{api_context}\n"
        f"<END CONTEXT>\n\n"
        f"PLAN:\n"
        f"{plan}\n\n"
        f"Based on the above plan, write Python code that constructs the described 3D model using CadQuery 2.\n"
        f"- Prefer using calculated values instead of hardcoded numbers. Ideally for positions use calculated values relative to other elements. Inline calculations if possible instead of making too many variables.\n"
        f"- Specify the positions and dimensions of elements relative and proportional to each other, only specifying numbers for one base element and calculating the rest from that.\n"
        f"- You may use specific points, edges or faces of a shape as reference for where to place other elements and what their dimensions are.\n"
        f"STRICT RULES:\n"
        f"- Use CadQuery ONLY through the existing variable named 'cq' which is already available in the environment.\n"
        f"- You can use safe python builtin functions and math functions via 'math'.\n"
        f"- Use only functions and classes that actually exist in cadquery from the API reference. Do NOT hallucinate anything.\n"
        f"- Do NOT import anything. No 'import cadquery', No 'import math', no imports of any kind.\n"
        f"- Define a function build() with no arguments.\n"
        f"- build() MUST return the final CadQuery Workplane or Shape.\n"
        f"- Define ONLY the build() function, no additional code outside of it. Like Following:\n"
        f"```\ndef build():\n"
        f"    # Your code here\n"
        f"    return result\n```\n"
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
        f"<CONTEXT>\n"
        f"{api_context}\n"
        f"<END CONTEXT>\n\n"
        f"A CadQuery script generated based on the following plan has failed with an error:\n\n"
        f"<PLAN>\n"
        f"{plan}\n"
        f"<END PLAN>\n\n"
        f"The following CadQuery code failed:\n\n"
        f"{numbered_code}\n\n"
        f"Error:\n{error_text}\n"
        f"Previous errors and fixes history (if any):\n{history_text}\n\n"
        f"Diagnose the error and propose a fix plan.\n"
        f"Make sure to stick to the original plan and the fix should align with it and should not change the original intent.\n"
        f"STRICT RULES:\n"
        f"- Use only functions and classes that actually exist in cadquery from the API reference.\n"
        f"- If the error is an import, know that cq and math are already in scope — nothing else is allowed.\n"
        f"- If statements span multiple lines, note all affected lines.\n"
        f"- Explain the cause and which lines need modification.\n"
        f"- Do NOT propose code yet, just provide a clear diagnosis and fix plan.\n"
        f"- Output only plain text.\n"
    )


def regen_prompt(plan: str, api_context: str, numbered_code: str, diagnosis: str) -> str:
    return (
        f"You are an expert CadQuery programmer. You have access to the full CadQuery 2 API.\n"
        f"<CONTEXT>\n"
        f"{api_context}\n"
        f"<END CONTEXT>\n\n"
        f"A CadQuery script generated based on the following plan has failed with an error:\n\n"
        f"<PLAN>\n"
        f"{plan}\n"
        f"<END PLAN>\n\n"
        f"The following CadQuery code failed:\n\n"
        f"{numbered_code}\n\n"
        f"The proposed diagnosis/fix plan:\n\n{diagnosis}\n\n"
        f"Regenerate the FULL corrected code and provide a brief summary of the fix.\n"
        f"Follow the coding style of the original code as much as possible, only changing what is necessary to fix the error based on the diagnosis.\n"
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
