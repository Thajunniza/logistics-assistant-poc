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
- Token usage tracking — every call (and every retry) recorded to SQLite
  with full attribution: app, user, agent, model, risk, tokens, cost, latency
"""

from __future__ import annotations

import os
import re
import json
import time
import logging
from typing import Type, Optional, List, Tuple

import litellm
from pydantic import BaseModel
from pydantic_core import ValidationError

from backend.token_tracker import (
    record_call,
    extract_usage_from_response,
    DEFAULT_APP_NAME,
)

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
    # ---- NEW: token tracking attribution ----
    agent_name: str = "unknown",
    user_name: str = "system",
    application_name: str = DEFAULT_APP_NAME,
    risk_id: Optional[str] = None,
) -> BaseModel:
    """
    Make one LLM call and validate response into response_model.

    Flow:
    1) Call model
    2) Try to validate any JSON object in output
    3) If none validate -> one schema-repair retry -> validate again

    Token usage is recorded for every underlying LLM call, including the
    repair retry. If the call fails entirely, a row is recorded with success=0.
    """

    if model is None:
        model = os.getenv("LITELLM_MODEL", "sap/gpt-4o")

    # SAP Gen AI Hub proxy strips response_format, so we enforce JSON at the
    # prompt layer. Append the target schema and a strict instruction to the
    # system prompt so the model sees exactly what to produce.
    schema = response_model.model_json_schema()
    schema_str = json.dumps(schema, indent=2)
    system_prompt = (
        system_prompt.rstrip()
        + "\n\n"
        + "You MUST respond with a single valid JSON object that conforms exactly "
        + "to the schema below. No prose, no preamble, no markdown, no code fences. "
        + "Output ONLY the JSON object.\n\n"
        + "JSON SCHEMA:\n"
        + schema_str
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    def _do_call(msgs, temp, *, retry_label: str) -> Tuple[str, int, int, int]:
        """
        Make one LLM call, return (content, prompt_tokens, completion_tokens, latency_ms).
        Records a tracking row on failure; success rows are recorded by the caller
        (so we can mark success only after schema validation passes).
        """
        started = time.time()
        try:
            resp = litellm.completion(
                model=model,
                messages=msgs,
                temperature=temp,
                max_tokens=max_tokens,
            )
            prompt_tok, completion_tok = extract_usage_from_response(resp)
            latency_ms = int((time.time() - started) * 1000)
            content = (resp["choices"][0]["message"]["content"] or "").strip()
            return content, prompt_tok, completion_tok, latency_ms

        except Exception as e:
            # API-level failure (network, auth, rate-limit). Record the failure and re-raise.
            latency_ms = int((time.time() - started) * 1000)
            record_call(
                agent_name=f"{agent_name} [{retry_label}]" if retry_label else agent_name,
                model=model,
                prompt_tokens=0,
                completion_tokens=0,
                user_name=user_name,
                application_name=application_name,
                risk_id=risk_id,
                latency_ms=latency_ms,
                success=False,
                error_message=f"API call failed: {type(e).__name__}: {str(e)[:300]}",
            )
            raise

    # ---------------------------
    # Attempt 1
    # ---------------------------
    raw_1, p1, c1, lat1 = _do_call(messages, temperature, retry_label="")

    validated = _try_validate_any_candidate(response_model, raw_1)
    if validated is not None:
        # Success on first try — record one successful call
        record_call(
            agent_name=agent_name,
            model=model,
            prompt_tokens=p1,
            completion_tokens=c1,
            user_name=user_name,
            application_name=application_name,
            risk_id=risk_id,
            latency_ms=lat1,
            success=True,
        )
        return validated

    # First attempt didn't yield valid JSON — record the failed attempt
    record_call(
        agent_name=agent_name,
        model=model,
        prompt_tokens=p1,
        completion_tokens=c1,
        user_name=user_name,
        application_name=application_name,
        risk_id=risk_id,
        latency_ms=lat1,
        success=False,
        error_message=f"Attempt 1: no JSON candidate validated for {response_model.__name__}",
    )

    logger.debug("Schema validation failed. Attempting one repair retry for %s", response_model.__name__)

    # Build the most informative repair message we can
    candidates = _find_json_objects(_strip_trailing_commas(_extract_fenced_block(raw_1)))
    first_err: Exception = ValidationError.from_exception_data("ValidationError", [])
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

    # ---------------------------
    # Attempt 2 (repair retry)
    # ---------------------------
    raw_2, p2, c2, lat2 = _do_call(retry_messages, temp=0.0, retry_label="repair-retry")

    validated_2 = _try_validate_any_candidate(response_model, raw_2)
    if validated_2 is not None:
        # Repair succeeded — record successful retry
        record_call(
            agent_name=f"{agent_name} [repair-retry]",
            model=model,
            prompt_tokens=p2,
            completion_tokens=c2,
            user_name=user_name,
            application_name=application_name,
            risk_id=risk_id,
            latency_ms=lat2,
            success=True,
        )
        return validated_2

    # Repair retry also failed — record it
    record_call(
        agent_name=f"{agent_name} [repair-retry]",
        model=model,
        prompt_tokens=p2,
        completion_tokens=c2,
        user_name=user_name,
        application_name=application_name,
        risk_id=risk_id,
        latency_ms=lat2,
        success=False,
        error_message=f"Repair retry also failed for {response_model.__name__}",
    )

    snippet = raw_2[:700].replace("\n", "\\n")
    raise ValueError(
        f"LLM output could not be validated for schema {response_model.__name__} even after repair.\n"
        f"Snippet (first 700 chars): {snippet}"
    )
