import traceback
import cadquery as cq
import textwrap
import json
import math
from dataclasses import dataclass
from pydantic import BaseModel, Field, model_validator
from typing import Literal, Optional
from bs4 import BeautifulSoup

import llm


@dataclass
class ExecutionError:
    # Which phase failed
    stage: str                       # "exec", "missing_build", "build"

    # Core error info
    error_type: str                  # e.g., "TypeError"
    message: str                     # e.g., "Workplane.loft() got ..."
    traceback: str                   # full formatted traceback string

    # Location info (may be None)
    file: Optional[str]
    line: Optional[int]
    function: Optional[str]


def extract_error_info(e: Exception, stage: str) -> ExecutionError:
    tb = e.__traceback__

    # Try to get the last frame (deepest point where the error happened)
    last_tb = tb
    while last_tb and last_tb.tb_next:
        last_tb = last_tb.tb_next

    if last_tb is None:
        file = line = function = None
    else:
        frame = last_tb.tb_frame
        file = frame.f_code.co_filename
        line = last_tb.tb_lineno
        function = frame.f_code.co_name

    return ExecutionError(
        stage=stage,
        error_type=type(e).__name__,
        message=str(e),
        traceback="".join(traceback.format_exception(type(e), e, tb)),
        file=file,
        line=line,
        function=function
    )


class FixOpModel(BaseModel):
    """
    A code-edit operation. Supports either:
    - Single line: provide 'line'
    - Multi-line range: provide both 'start' and 'end'

    RULES:
    - Provide exactly **one** of:
        • line=<int>
        • start=<int> and end=<int>
    - For replace/insert_after, 'new' must contain the inserted code.
    """

    op: Literal["replace", "delete", "insert_after"] = Field(
        description="Type of operation"
    )

    line: Optional[int] = Field(
        default=None,
        description="Single line number (if applying to exactly one line)"
    )
    start: Optional[int] = Field(
        default=None,
        description="Start line number of the range"
    )
    end: Optional[int] = Field(
        default=None,
        description="End line number of the range (inclusive)"
    )

    new: Optional[str] = Field(
        default=None,
        description="New code for replace/insert operations"
    )

    @model_validator(mode="after")
    def validate_line_spec(self):
        # You must provide exactly one: either 'line' OR ('start' and 'end')
        line = self.line
        start = self.start
        end = self.end

        # Check mutual exclusivity
        if line is not None and (start is not None or end is not None):
            raise ValueError("Specify either 'line' or ('start' and 'end'), not both.")

        # Check range validity
        if (start is not None) != (end is not None):
            raise ValueError("'start' and 'end' must be provided together.")

        if start is not None and end is not None and start > end:
            raise ValueError("'start' must be <= 'end'.")

        # Check at least one form specified
        if line is None and (start is None or end is None):
            raise ValueError("Provide either 'line' or ('start' and 'end').")

        return self


class FixDiffModel(BaseModel):
    diff: list[FixOpModel] = Field(description="List of code modification operations")
    summary: str = Field(description="Brief description of the fix attempted")


def load_api_context(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        html = f.read()

    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(separator="")
    return text


cq_api_context = load_api_context("data/cadquery_api_reference.html")

def generate_plan(prompt: str) -> str:
    plan_prompt = (
        f"Design a precise 3D model for: {prompt}.\n"
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
        # f"- Use cadquery API reference for a feasable plan: https://cadquery.readthedocs.io/en/latest/apireference.html\n"
    )
    return llm.generate_text(plan_prompt)


def generate_cadquery_code(plan: str) -> str:
    code_prompt = (
        f"You are an expert CadQuery programmer. You have access to the full CadQuery 2 API.\n"
        f"CONTEXT: <API REFERENCE>\n"
        f"{cq_api_context}\n"
        f"<END API REFERENCE>\n\n"
        f"PLAN:\n"
        f"{plan}\n"
        f"\n"
        f"Based on the above plan, write Python code that constructs the described 3D model using CadQuery 2.\n"
        f"STRICT RULES:\n"
        f"- Use CadQuery ONLY through the existing variable named 'cq' which is already available in the environment.\n"
        f"- You can use safe python builtin functions and math functions via 'math'.\n"
        f"- Use only functions and classes that actually exist in cadquery from the API reference. Do NOT hallucinate anything.\n"
        f"- Do NOT import anything. No 'import cadquery', No 'import math', no imports of any kind as cq and math are already available in the execution environment.\n"
        f"- Define a function build() with no arguments.\n"
        f"- build() must return the final CadQuery Workplane or Shape.\n"
        f"- Define ONLY the build() function, no additional code outside of it.\n"
        f"- Do NOT export files.\n"
        f"- Do NOT include comments.\n"
        f"- Generate the code as text, DO NOT try to execute it yourself.\n"
        f"- Output ONLY pure Python code, NO markdown formatting, NO surrounding text.\n"
    )
    code_prompt = textwrap.dedent(code_prompt)
    code = llm.generate_text(code_prompt)
    # remove markdown formatting if any
    if code.startswith("```") and code.endswith("```"):
        code = "\n".join(code.splitlines()[1:-1])
    return code



def fix_code_once(plan: str, original_code: str, error: ExecutionError, fix_history: list[dict["error": str, "summary": str]] = [], verbose=False) -> str:
    # 1. Number the code
    numbered_lines = [f"{i+1:04d}| {line}" for i, line in enumerate(original_code.splitlines())]
    numbered_code = "\n".join(numbered_lines)
    if verbose:
        print("Numbered Code:\n", numbered_code)

    # 2. Diagnosis prompt
    
    # Prepare previous fixes as text
    history_text = ""
    if fix_history:
        history_lines = []
        for i, h in enumerate(fix_history, start=1):
            history_lines.append(f"{i}. Error: {h['error']}\n   Fix attempted: {h['summary']}")
        history_text = "\nPrevious fixes:\n" + "\n".join(history_lines)

    error_text = f"Error occurred on line {error.line}:\n{error.error_type}: {error.message}\n{error.traceback}"

    diagnosis_prompt = (
        f"You are an expert CadQuery programmer. You have access to the full CadQuery 2 API.\n"
        f"CONTEXT: <API REFERENCE>\n"
        f"{cq_api_context}\n"
        f"<END API REFERENCE>\n\n"
        f"<PLAN>\n\n"
        f"The user provided the following plan for a 3D model:\n"
        f"{plan}\n"
        f"<END PLAN>\n\n"
        f"The following Python CadQuery 2 code failed to create the model based on the above plan failed:\n\n"
        f"{numbered_code}\n\n"
        f"Error:\n{error_text}\n"
        f"{history_text}\n\n"
        f"STRICT RULES:\n"
        f"- Use only functions and classes that actually exist in cadquery from the API reference. Do NOT hallucinate anything.\n"
        f"- Make sure the proposed changes do not change the model outcome.\n"
        f"- If error is related to execution environment, know that cq and math are already available in the env so they don't need to be imported, and if anything else is attempted to be imported that should not be allowed.\n"
        f"- If certain statements span multiple lines, make sure to indicate change in all affected lines to maintain correct syntax\n"
        f"- Explain the cause of the error and which line(s) need modification.\n"
        f"- Do NOT propose code yet, just provide a clear diagnosis and fix plan.\n"
        f"- Output only plain text."
    )

    diagnosis = llm.generate_text(diagnosis_prompt)
    if verbose:
        print("Diagnosis/Plan:\n", diagnosis)

    # 3. Structured diff prompt
    diff_prompt = (
        f"You have the numbered code:\n\n{numbered_code}\n\n"
        f"and the diagnosis/fix plan:\n\n{diagnosis}\n\n"
        f"Generate a structured JSON diff to fix the code AND include a short summary of the attempted fix.\n"
        f"RULES:\n"
        f"- Do not rewrite the whole file.\n"
        f"- Do not add imports.\n"
        f"- Only modify lines indicated.\n"
        f"- Use line numbers as given.\n"
        f"- Make sure to maintain the correct indent when inserting/replacing new line.\n"
        f"- If certain statements span multiple lines, make sure to indicate change in all affected lines to maintain correct syntax, such as correct closing backet for open bracket in earlier line.\n"
        f"- Keep the summary concise (1-2 sentences)."
    )
    diff: FixDiffModel = llm.generate_structured(diff_prompt, FixDiffModel)

    # 4. Apply diff using line-number mapping
    # Build line map
    lines = original_code.splitlines()
    n = len(lines)

    replacements = {}          # line_no -> new_text (for single-line replace)
    range_replacements = []    # (start, end, new_text)
    deletions = set()          # set of individual line numbers to delete
    range_deletions = []       # list of (start, end)
    insertions = {}            # line_no -> list of new lines
    range_insertions = []      # list of (start, end, new_text)

    for op in diff.diff:
        typ = op.op
        new_text = op.new

        if op.line is not None:
            # single-line operation
            start = end = op.line
        else:
            start = op.start
            end = op.end

        if typ == "replace":
            if start == end:
                replacements[start] = new_text
            else:
                range_replacements.append((start, end, new_text))

        elif typ == "delete":
            if start == end:
                deletions.add(start)
            else:
                range_deletions.append((start, end))

        elif typ == "insert_after":
            if start == end:
                insertions.setdefault(start, []).append(new_text)
            else:
                range_insertions.append((start, end, new_text))

        else:
            raise ValueError(f"Unknown diff operation: {typ}")

    # --- Construct output ---
    final_lines = []
    ln = 1

    while ln <= n:
        line_text = lines[ln - 1]

        # --- Check deletions ---
        if ln in deletions:
            ln += 1
            continue

        deleted_by_range = False
        for rs, re in range_deletions:
            if rs <= ln <= re:
                deleted_by_range = True
                break

        if deleted_by_range:
            ln += 1
            continue

        # --- Check replacements ---
        if ln in replacements:
            final_lines.append(replacements[ln])
            # After a replacement, still check for insertion_after this line
        else:
            # Check range replacements
            replaced = False
            for rs, re, new_text in range_replacements:
                if rs <= ln <= re:
                    # Only insert replacement text when encountering the first line of the range
                    if ln == rs:
                        final_lines.append(new_text)
                    replaced = True
                    break

            if not replaced:
                final_lines.append(line_text)

        # --- Handle insert_after ---
        if ln in insertions:
            final_lines.extend(insertions[ln])

        # For range insertions, only insert after the end of a range ONCE
        for rs, re, new_text in range_insertions:
            if ln == re:
                final_lines.append(new_text)

        ln += 1

    fixed_code = "\n".join(final_lines)
    return fixed_code, diff.summary


def run_cadquery_script(script: str):
    safe_builtins = {
        "abs": abs,
        "all": all,
        "any": any,
        "ascii": ascii,
        "bin": bin,
        "bool": bool,
        "bytearray": bytearray,
        "bytes": bytes,
        "callable": callable,
        "chr": chr,
        "classmethod": classmethod,
        "complex": complex,
        "dict": dict,
        "divmod": divmod,
        "enumerate": enumerate,
        "float": float,
        "format": format,
        "frozenset": frozenset,
        "hash": hash,
        "hex": hex,
        "int": int,
        "isinstance": isinstance,
        "issubclass": issubclass,
        "iter": iter,
        "len": len,
        "list": list,
        "map": map,
        "max": max,
        "min": min,
        "next": next,
        "oct": oct,
        "ord": ord,
        "pow": pow,
        "range": range,
        "repr": repr,
        "reversed": reversed,
        "round": round,
        "set": set,
        "slice": slice,
        "sorted": sorted,
        "staticmethod": staticmethod,
        "str": str,
        "sum": sum,
        "tuple": tuple,
        "zip": zip,
    }
    # safe_math = {k: getattr(math, k) for k in dir(math) if not k.startswith("_")}
    safe_globals = {
        "__builtins__": safe_builtins,
        "math": math,
        "cq": cq,
    }
    local_env = {}

    try:
        exec(script, safe_globals, local_env)
    except Exception as e:
        return None, extract_error_info(e, "exec")

    if "build" not in local_env:
        return None, ExecutionError(
            stage="missing_build",
            error_type="MissingBuildFunction",
            message="build() was not defined.",
            traceback="",
            file=None,
            line=None,
            function=None
        )


    try:
        result = local_env["build"]()
    except Exception as e:
        return None, extract_error_info(e, "build")

    return result, None


if __name__ == "__main__":
    prompt = input("Enter a description of the 3D model you want to generate: ")
    
    plan = generate_plan(prompt)
    # print("Plan:\n", plan)
    
    code = generate_cadquery_code(plan)
    # print("Generated Code:\n", code)
    
    # confirm = input("Confirm to execute (Y/N): ")
    # if confirm.lower() != 'y':
    #     print("Execution cancelled.")
    #     exit(0)

    attempt = 0
    max_attempts = 5
    fix_history = []
    while True :
        result, error = run_cadquery_script(code)
        if error:
            print("Error encountered:\n", error)
            if attempt >= max_attempts:
                print("Max attempts reached. Exiting.")
                break
            code, fix_summary = fix_code_once(plan, code, error, fix_history)
            fix_history.append({ "error": f"{error.error_type}: {error.message}", "summary": fix_summary })
            # print("Corrected Code:\n", code)
            attempt += 1
        else:
            cq.exporters.export(result, 'result.stl')
            print("3D model exported to result.stl")
            break
