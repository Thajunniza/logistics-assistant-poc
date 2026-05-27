"""
LiteLLM client wrapper for the Logistics Assistant POC.

Key features:
- Strict schema validation using Pydantic (typed boundary)
- Robust JSON extraction:
  * handles code fences
  * handles trailing commas
  * handles extra trailing characters
  * handles multiple JSON objects (tries each until one validates)
- One schema-repair retry if no JSON object validates
"""

from __future__ import annotations

import os
import re
import json
import logging
from typing import Type, Optional, List

import litellm
from pydantic import BaseModel
from pydantic_core import ValidationError

logger = logging.getLogger(__name__)

# Uncomment only when debugging provider issues
# litellm._turn_on_debug()

_CODE_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)


def _extract_fenced_block(text: str) -> str:
    """Extract content from ```json ...``` if present."""
    if not text:
        return text
    m = _CODE_FENCE_RE.search(text)
    return m.group(1).strip() if m else text.strip()


def _strip_trailing_commas(text: str) -> str:
    """Remove trailing commas before } or ] which break strict JSON."""
    return re.sub(r",\s*([}\]])", r"\1", text or "")


def _find_json_objects(text: str) -> List[str]:
    """
    Find candidate JSON object strings inside text by scanning braces.

    This is robust against:
    - extra narrative before/after JSON
    - multiple JSON objects in a single response
    """
    if not text:
        return []

    candidates = []
    s = text
    stack = 0
    start = None

    for i, ch in enumerate(s):
        if ch == "{":
            if stack == 0:
                start = i
            stack += 1
        elif ch == "}":
            if stack > 0:
                stack -= 1
                if stack == 0 and start is not None:
                    candidates.append(s[start : i + 1])
                    start = None

    # Return longer candidates first (often the “full object” vs small partial dict)
    candidates.sort(key=len, reverse=True)
    return candidates


def _clean_candidate_json(candidate: str) -> str:
    """Clean a JSON candidate safely."""
    c = candidate.strip()
    c = _strip_trailing_commas(c)
    c = c.strip()
    return c


def _try_validate_any_candidate(response_model: Type[BaseModel], raw_text: str) -> Optional[BaseModel]:
    """
    Try to validate any JSON object found in raw_text.
    Returns the first successfully validated model, else None.
    """
    text = _extract_fenced_block(raw_text)
    text = _strip_trailing_commas(text)

    for cand in _find_json_objects(text):
        cleaned = _clean_candidate_json(cand)
        try:
            return response_model.model_validate_json(cleaned)
        except Exception:
            continue

    return None


def _schema_repair_prompt(response_model: Type[BaseModel], err: Exception) -> str:
    """
    Build repair instruction including the schema and a short error summary.
    """
    schema = response_model.model_json_schema()
    schema_str = json.dumps(schema, indent=2)
    err_summary = f"{type(err).__name__}: {str(err)[:500]}"

    return (
        "Your previous response did not match the required JSON schema.\n"
        "Return ONLY valid JSON (no markdown, no code fences, no trailing commas) that matches this schema EXACTLY.\n\n"
        f"Schema:\n{schema_str}\n\n"
        f"Validation error summary:\n{err_summary}\n"
    )


def call_llm(
    system_prompt: str,
    user_message: str,
    response_model: Type[BaseModel],
    *,
    model: Optional[str] = None,
    temperature: float = 0.2,
    max_tokens: int = 900,
) -> BaseModel:
    """
    Make one LLM call and validate response into response_model.

    Flow:
    1) Call model
    2) Try to validate any JSON object in output
    3) If none validate -> one schema-repair retry -> validate again
    """

    if model is None:
        model = os.getenv("LITELLM_MODEL", "sap/gpt-4o")

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    def _do_call(msgs, temp) -> str:
        resp = litellm.completion(
            model=model,
            messages=msgs,
            temperature=temp,
            max_tokens=max_tokens,
        )
        return (resp["choices"][0]["message"]["content"] or "").strip()

    # ---------------------------
    # Attempt 1
    # ---------------------------
    raw_1 = _do_call(messages, temperature)

    validated = _try_validate_any_candidate(response_model, raw_1)
    if validated is not None:
        return validated

    # If we reach here, no candidate JSON validated; do one repair retry
    # Keep this log as DEBUG (not noisy for demo)
    logger.debug("Schema validation failed. Attempting one repair retry for %s", response_model.__name__)

    # Try to provide a meaningful error by validating the largest candidate (if any)
    candidates = _find_json_objects(_strip_trailing_commas(_extract_fenced_block(raw_1)))
    first_err: Exception = ValidationError.from_exception_data("ValidationError", [])  # fallback
    if candidates:
        try:
            response_model.model_validate_json(_clean_candidate_json(candidates[0]))
        except Exception as e:
            first_err = e

    repair = _schema_repair_prompt(response_model, first_err)

    retry_messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
        {"role": "user", "content": repair},
    ]

    raw_2 = _do_call(retry_messages, temp=0.0)

    validated_2 = _try_validate_any_candidate(response_model, raw_2)
    if validated_2 is not None:
        return validated_2

    # Still failing: raise a clean error with snippet
    snippet = raw_2[:700].replace("\n", "\\n")
    raise ValueError(
        f"LLM output could not be validated for schema {response_model.__name__} even after repair.\n"
        f"Snippet (first 700 chars): {snippet}"
    )