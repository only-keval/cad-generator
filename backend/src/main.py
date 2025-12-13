from llmclient.gemini import GeminiClient
from llmclient.ollama import OllamaClient
from agent.orchestrator import ModelAgentOrchestrator
from agent.planner_service import ModelPlanner
from agent.codegen_service import CqCodeGenerator
from agent.cadquery_executor import CadqueryExecutor
from agent.code_fixer_service import CodeFixerService

import cadquery as cq
from dotenv import load_dotenv
import os


def load_api_context(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


if __name__ == "__main__":
    if not load_dotenv():
        print("ERROR: .env file not found or could not be loaded.")
        os.exit(1)

    llm = GeminiClient(api_key=os.environ["GEMINI_API_KEY"], model="gemini-2.5-flash")
    # llm = GeminiClient(api_key=os.environ["GEMINI_API_KEY"], model="gemini-2.5-flash-lite")
    # llm = OllamaClient(model="qwen2.5-coder:7b")
    # llm = OllamaClient(model="mistral:latest")
    api_context = load_api_context("data/cadquery_api_reference.txt")

    agent = ModelAgentOrchestrator(
        planner=ModelPlanner(llm, api_context),
        code_generator=CqCodeGenerator(llm, api_context),
        executor=CadqueryExecutor(),
        code_fixer=CodeFixerService(llm, api_context)
    )

    user_request = input("Enter your 3D model request: ")
    model, error = agent.build_model(user_request)

    if error is not None:
        print("Failed to build model after multiple attempts.")
        print(f"Last error: {error.error_type}: {error.message}")
    else:
        print("Model built successfully.")
        cq.exporters.export(model, "result.stl")
        print("Model exported to result.stl")
