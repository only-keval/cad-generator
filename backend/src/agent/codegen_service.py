from llmclient.interfaces import LLMClient


def process_code(code: str) -> str:
    code_lines = code.splitlines()
        
    # remove markdown formatting if any
    if code.startswith("```") and code.endswith("```"):
        code_lines = code_lines[1:-1]

    # remove import lines if somehow slipped though the model
    filtered_lines = [line for line in code_lines if not line.strip().startswith("import ")]
    
    code = "\n".join(filtered_lines)

    return code


class CqCodeGenerator:
    def __init__(self, llm: LLMClient, api_context: str):
        self.llm = llm
        self.api_context = api_context
    
    
    def generate_code(self, model_plan: str) -> str:
        code_prompt = (
            f"You are an expert CadQuery programmer. You have access to the full CadQuery 2 API.\n"
            f"CONTEXT: <API REFERENCE>\n"
            f"{self.api_context}\n"
            f"<END API REFERENCE>\n\n"
            f"PLAN:\n"
            f"{model_plan}\n"
            f"\n"
            f"Based on the above plan, write Python code that constructs the described 3D model using CadQuery 2.\n"
            f"STRICT RULES:\n"
            f"- Use CadQuery ONLY through the existing variable named 'cq' which is already available in the environment.\n"
            f"- You can use safe python builtin functions and math functions via 'math'.\n"
            f"- Use only functions and classes that actually exist in cadquery from the API reference. Do NOT hallucinate anything. Use ONLY the definitions specified in the api reference.\n"
            f"- Do NOT import anything. No 'import cadquery', No 'import math', no imports of any kind as cq and math are already available in the execution environment.\n"
            f"- Define a function build() with no arguments.\n"
            f"- build() must return the final CadQuery Workplane or Shape.\n"
            f"- Define ONLY the build() function, no additional code outside of it.\n"
            f"- Do NOT export files.\n"
            f"- Do NOT include comments.\n"
            f"- Generate the code as text, DO NOT try to execute it yourself.\n"
            f"- Output ONLY pure Python code, NO markdown formatting, NO surrounding text.\n"
        )
        
        code = self.llm.generate_text(code_prompt)
        code = process_code(code)
        return code
