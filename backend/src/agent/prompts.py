from typing import Optional


def description_prompt(user_request: str) -> str:
    return (
        f"Convert the user's 3D modeling request into a precise functional design specification.\n\n"

        f"User request:\n{user_request}\n\n"

        f"Write a short technical description using clear, explicit statements.\n\n"

        f"Include the following:\n"
        f"- Object type and purpose\n"
        f"- Whether it is solid or hollow\n"
        f"- Main components (list them explicitly)\n"
        f"- Shape of each component (e.g., cylindrical body, rectangular handle)\n"
        f"- How components are positioned relative to each other\n"
        f"- Whether the object is open or closed\n\n"

        f"Rules:\n"
        f"- Use simple, direct sentences\n"
        f"- Avoid stylistic or aesthetic language (no words like 'smooth', 'elegant', 'ergonomic')\n"
        f"- Be explicit about geometry and function\n"
        f"- Do not omit important structural details\n"
        f"- Do not mention implementation, CAD, or code\n\n"

        f"Output only the description.\n"
    )

def plan_prompt(description: str) -> str:
    return (
        f"Design a precise 3D model for: {description}.\n\n"

        f"You MUST output a structured JSON object describing the model.\n"
        f"Do NOT include any explanation, text, or markdown. Output ONLY valid JSON.\n\n"

        f"Use CadQuery coordinate system conventions:\n"
        f"- +Z is up\n"
        f"- XY plane is the base\n"
        f"- +X is right, +Y is forward\n\n"

        f"OUTPUT FORMAT:\n"
        f"{{\n"
        f'  "primitives": [\n'
        f"    {{\n"
        f'      "id": "string",\n'
        f'      "type": "box | cylinder | sphere | cone",\n'
        f'      "dimensions": {{...}},\n'
        f'      "position": [x, y, z],\n'
        f'      "orientation": "X | Y | Z"\n'
        f"    }}\n"
        f"  ],\n"
        f'  "constraints": [\n'
        f"    {{\n"
        f'      "type": "center | stack | offset",\n'
        f'      "target": "primitive_id",\n'
        f'      "reference": "primitive_id",\n'
        f'      "axis": "X | Y | Z",\n'
        f'      "value": number (only for offset),\n'
        f'      "axes": ["X","Y","Z"] (only for center)\n'
        f"    }}\n"
        f"  ]\n"
        f"}}\n\n"

        f"RULES FOR PRIMITIVES:\n"
        f"- Each primitive must have a unique id.\n"
        f"- Use only allowed types.\n"
        f"- Dimensions must be in millimeters and positive.\n"
        f"- Box: length, width, height.\n"
        f"- Cylinder: radius, height.\n"
        f"- Sphere: radius.\n"
        f"- Cone: radius, height.\n"
        f"- The FIRST primitive is the base and MUST have position [0, 0, 0].\n"
        f"- All orientations must be exactly one of X, Y, Z.\n\n"

        f"RULES FOR CONSTRAINTS:\n"
        f"- Constraints must reference valid primitive ids.\n"
        f"- center: use 'axes' field, do NOT use 'axis' or 'value'.\n"
        f"- stack: place target on top of reference along the given axis.\n"
        f"- offset: move target along axis by value.\n"
        f"- Do NOT include unnecessary constraints.\n\n"

        f"SPATIAL RULES:\n"
        f"- Build from bottom to top along +Z.\n"
        f"- Do NOT place objects below Z = 0 unless explicitly required.\n"
        f"- Prefer center + stack instead of manually setting positions.\n"
        f"- Avoid redundant or conflicting constraints.\n\n"
    )


def codegen_prompt(plan: str, api_context: str) -> str:
    return (
        f"You are an expert CadQuery programmer. You have access to the full CadQuery 2 API.\n\n"

        f"<CONTEXT>\n"
        f"{api_context}\n"
        f"<END CONTEXT>\n\n"

        f"<PLAN_JSON>\n"
        f"{plan}\n"
        f"<END PLAN_JSON>\n\n"

        f"IMPORTANT:\n"
        f"- The PLAN_JSON is the single source of truth.\n"
        f"- Do NOT reinterpret, redesign, or infer anything beyond what is explicitly defined.\n"
        f"- Use primitives and constraints exactly as specified.\n"
        f"- Do NOT invent new dimensions, relationships, or primitives.\n\n"

        f"INSTRUCTIONS:\n"
        f"- Generate Python code using CadQuery 2 that constructs the model described in PLAN_JSON.\n"
        f"- Build the model starting from the base primitive (first in the list).\n"
        f"- Apply constraints step-by-step (center, stack, offset).\n"
        f"- Respect all axis directions strictly (X, Y, Z).\n"
        f"- Use Workplane('XY') as the base unless otherwise required.\n\n"

        f"GEOMETRY RULES:\n"
        f"- All vertical construction must follow +Z unless explicitly specified otherwise.\n"
        f"- Do NOT place objects below Z = 0 unless defined in the plan.\n"
        f"- Maintain exact relative positioning from constraints.\n\n"

        f"CONTEXT USAGE:\n"
        f"- Use the CONTEXT as the source of truth for CadQuery API usage.\n"
        f"- Prefer patterns and examples from CONTEXT over prior knowledge.\n"
        f"- Do NOT use methods or signatures not supported by CONTEXT.\n\n"

        f"STRICT RULES:\n"
        f"- Use CadQuery ONLY through the existing variable named 'cq'.\n"
        f"- You can use safe python builtin functions and math functions via 'math'.\n"
        f"- Do NOT import anything.\n"
        f"- Define a function build() with no arguments.\n"
        f"- build() MUST return the final CadQuery Workplane or Shape.\n"
        f"- Define ONLY the build() function, no additional code outside of it.\n"
        f"- Do NOT export files.\n"
        f"- Do NOT include comments.\n"
        f"- Output ONLY pure Python code, NO markdown, NO extra text.\n"
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
