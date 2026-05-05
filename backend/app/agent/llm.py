import json
import logging
import os
from typing import Type, TypeVar

import litellm
import instructor
from litellm import completion
from litellm.exceptions import ServiceUnavailableError, RateLimitError
from pydantic import BaseModel

litellm.set_verbose = False
litellm.suppress_debug_info = True
for _name in ["litellm", "LiteLLM", "litellm.utils", "litellm.main", "httpx", "httpcore"]:
    logging.getLogger(_name).setLevel(logging.CRITICAL)

T = TypeVar("T", bound=BaseModel)
_instructor = instructor.from_litellm(completion)


def _model() -> str:
    return os.environ.get("LLM_MODEL", "groq/llama-3.3-70b-versatile")

def _fallbacks() -> list[str]:
    raw = os.environ.get("LLM_FALLBACKS", "")
    return [m.strip() for m in raw.split(",") if m.strip()]

def _models() -> list[str]:
    chain = [_model(), *_fallbacks()]
    seen = set()
    return [m for m in chain if m and not (m in seen or seen.add(m))]

def _is_rate_limit(exc: Exception) -> bool:
    return (
        getattr(exc, "status_code", None) == 429
        or "429" in str(exc)
        or "rate limit" in str(exc).lower()
        or "ratelimit" in str(exc).lower()
    )


def _should_fallback(exc: Exception) -> bool:
    return _is_rate_limit(exc) or isinstance(exc, RateLimitError) or isinstance(exc, ServiceUnavailableError)


def llm(prompt: str) -> str:
    models = _models()
    for i, model in enumerate(models):
        try:
            res = completion(model=model, messages=[{"role": "user", "content": prompt}])
            return res.choices[0].message.content or ""
        except Exception as exc:
            if _should_fallback(exc) and i + 1 < len(models):
                print(f"[llm] fallback on '{model}', switching to '{models[i + 1]}'")
                continue
            raise
    raise RuntimeError("All models failed.")


def llm_structured(prompt: str, schema: Type[T], max_retries: int = 3) -> T:
    models = _models()
    for i, model in enumerate(models):
        try:
            return _instructor.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                response_model=schema,
                max_retries=max_retries,
            )
        except Exception as exc:
            if _should_fallback(exc) and i + 1 < len(models):
                print(f"[llm] fallback on '{model}', switching to '{models[i + 1]}'")
                continue
            raise
    raise RuntimeError("All models failed.")