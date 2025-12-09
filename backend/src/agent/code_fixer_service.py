from .cadquery_executor import ExecutionError
from llmclient.interfaces import LLMClient
from typing import Literal, Optional
from pydantic import BaseModel, Field, model_validator


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


class CodeFixerService:
    def __init__(self, llm: LLMClient, api_context: str):
        self.llm = llm
        self.api_context = api_context


    def diagnose(self, plan: str, numbered_code: str, error: ExecutionError, history: list) -> str:
        history_text = ""
        if history:
            history_lines = []
            for i, h in enumerate(history, start=1):
                history_lines.append(f"{i}. Error: {h['error']}\n   Fix attempted: {h['summary']}")
            history_text = "\nPrevious fixes:\n" + "\n".join(history_lines)

        error_text = f"Error occurred on line {error.line}:\n{error.error_type}: {error.message}\n{error.traceback}"

        diagnosis_prompt = (
            f"You are an expert CadQuery programmer. You have access to the full CadQuery 2 API.\n"
            f"CONTEXT: <API REFERENCE>\n"
            f"{self.api_context}\n"
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

        return self.llm.generate_text(diagnosis_prompt)
        

    def propose_diff(self, numbered_code: str, diagnosis: str) -> FixDiffModel:
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
        return self.llm.generate_structured(diff_prompt, FixDiffModel)


    def apply_diff(self, original_code: str, diff: FixDiffModel) -> str:
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
        return fixed_code
    

    def fix_code_once(self, plan: str, original_code: str, error: ExecutionError, fix_history: list[dict["error": str, "summary": str]] = []) -> tuple[str, str]:
        numbered_lines = [f"{i+1:04d}| {line}" for i, line in enumerate(original_code.splitlines())]
        numbered_code = "\n".join(numbered_lines)
        diagnosis = self.diagnose(plan, numbered_code, error, fix_history)
        diff = self.propose_diff(numbered_code, diagnosis)
        fixed_code = self.apply_diff(original_code, diff)
        return fixed_code, diff.summary
    
