from .interfaces import LLMClient, T

from google import genai
from pydantic import BaseModel

class GeminiClient(LLMClient):
    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        self.client = genai.Client(api_key=api_key)
        self.model = model

    def generate_text(self, prompt: str) -> str:
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
        )
        return response.text


    def generate_structured(self, prompt: str, schema: type[T]) -> T:
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_json_schema": schema.model_json_schema(),
            }
        )

        return schema.model_validate_json(response.text)
