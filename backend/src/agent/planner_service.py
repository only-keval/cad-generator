from llmclient.interfaces import LLMClient

class ModelPlanner:
    def __init__(self, llm: LLMClient, api_context: str):
        self.llm = llm
        self.api_context = api_context


    def plan_model(self, user_request: str) -> str:
        plan_prompt = (
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
        return self.llm.generate_text(plan_prompt)
