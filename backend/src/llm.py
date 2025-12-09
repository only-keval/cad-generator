from google import genai
from google.genai.types import Tool, GenerateContentConfig
from dotenv import load_dotenv
from pydantic import BaseModel
import os

if not load_dotenv():
    print("ERROR: .env file not found or could not be loaded.")
    os.exit(1)


MODEL = "gemini-2.5-flash-lite"
tools = [
  {"url_context": {}},
]
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

VERBOSE = True

def generate_text(prompt: str) -> str:
    if VERBOSE:
        print("\nLLM Prompt:")
        print(prompt)

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
    )

    if VERBOSE:
        print("\nLLM Response:")
        print(response.text)

    return response.text


def generate_structured(prompt: str, schema: type[BaseModel]):
    if VERBOSE:
        print("\nLLM Prompt (Structured):")
        print(prompt)

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_json_schema": schema.model_json_schema(),
        }
    )

    if VERBOSE:
        print("\nLLM Structured Response:")
        print(response.text)

    return schema.model_validate_json(response.text)
