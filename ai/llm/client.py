"""LLM client — wraps LiteLLM with structured output validation."""
from __future__ import annotations
import json
import logging
from typing import Type, TypeVar

import litellm
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)


def call_llm(
    system_prompt: str,
    user_message: str,
    response_model: Type[T],
    model: str = "sap/gpt-4o",
    temperature: float = 0.2,
) -> T:
    """
    Call the LLM and return a validated instance of response_model.
    Forces JSON output by appending the schema to the system prompt.
    """
    schema = json.dumps(response_model.model_json_schema(), indent=2)
    full_system = (
        f"{system_prompt}\n\n"
        f"Return ONLY a JSON object (no markdown fences, no preamble, no commentary) "
        f"that matches exactly this JSON schema:\n{schema}"
    )

    response = litellm.completion(
        model=model,
        messages=[
            {"role": "system", "content": full_system},
            {"role": "user", "content": user_message},
        ],
        temperature=temperature,
    )

    raw = response.choices[0].message.content or ""
    cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    try:
        return response_model.model_validate_json(cleaned)
    except ValidationError as e:
        logger.error("Invalid LLM JSON for %s\nError: %s\nRaw: %s", response_model.__name__, e, raw[:500])
        raise