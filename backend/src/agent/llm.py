import os
import litellm
from typing import TypeVar, Type
from litellm import completion
from pydantic import BaseModel
import logging

logging.getLogger("litellm").setLevel(logging.WARNING)
logging.getLogger("LiteLLM").setLevel(logging.WARNING)

litellm.suppress_debug_info = True
litellm.set_verbose = False

T = TypeVar("T", bound=BaseModel)

def _model() -> str:
    return os.environ.get("LLM_MODEL", "groq/llama-3.3-70b-versatile")

def _fallbacks() -> list[str]:
    raw = os.environ.get("LLM_FALLBACKS", "")
    return [m.strip() for m in raw.split(",") if m.strip()]

def llm(prompt: str) -> str:
    res = completion(
        model=_model(),
        messages=[{"role": "user", "content": prompt}],
        fallbacks=_fallbacks() or None,
    )
    return res.choices[0].message.content or ""

def llm_structured(prompt: str, schema: Type[T]) -> T:
    res = completion(
        model=_model(),
        messages=[
            {"role": "system", "content": "Return only valid JSON matching the schema. No markdown fences, no extra text."},
            {"role": "user", "content": prompt},
        ],
        response_format=schema,
        fallbacks=_fallbacks() or None,
    )
    return schema.model_validate_json(res.choices[0].message.content or "{}")