from .interfaces import LLMClient, T
import ollama
from typing import Optional

class OllamaClient(LLMClient):
    def __init__(self, model: str, host: Optional[str] = None):
        self.client = ollama.Client(host=host)
        self.model = model

    def generate_text(self, prompt: str) -> str:
        response = self.client.generate(
            model=self.model, 
            prompt=prompt
        )
        return response.response

    def generate_structured(self, prompt: str, schema: type[T]) -> T:
        response = self.client.generate(
            model=self.model, 
            prompt=prompt, 
            format=schema.model_json_schema()
        )
        return schema.model_validate_json(response.response)
        
