from .codegen_service import CqCodeGenerator
from .cadquery_executor import CadqueryExecutor
from .code_fixer_service import CodeFixerService
from .planner_service import ModelPlanner
from typing import Optional
import cadquery as cq
from .cadquery_executor import ExecutionError

class ModelAgentOrchestrator:
    def __init__(self, 
        planner: ModelPlanner,
        code_generator: CqCodeGenerator,
        executor: CadqueryExecutor,
        code_fixer: CodeFixerService
    ):
        self.planner = planner
        self.code_generator = code_generator
        self.executor = executor
        self.code_fixer = code_fixer


    def build_model(self, user_request: str) -> tuple[Optional[cq.Shape | cq.Workplane], Optional[ExecutionError]]:
        print("Planning model...")
        plan = self.planner.plan_model(user_request)
        print(f"Plan:\n{plan}\n")
        print("Generating code...")
        code = self.code_generator.generate_code(plan)
        print(f"Generated Code:\n{code}\n")

        attempt = 0
        max_attempts = 5
        fix_history = []
        while True :
            print(f"Executing code (Attempt {attempt + 1})...")
            result, error = self.executor.run_cadquery_script(code)
            if error:
                print(f"Execution error:\n{error.error_type}: {error.message}\n")
                if attempt >= max_attempts:
                    print("Max attempts reached. Exiting.")
                    return None, error
                print("Attempting to fix code...")
                code, fix_summary = self.code_fixer.fix_code_once(plan, code, error, fix_history)
                print(f"Fixed Code:\n{code}\n")
                fix_history.append({ "error": f"{error.error_type}: {error.message}", "summary": fix_summary })
                attempt += 1
            else:
                return result, None
