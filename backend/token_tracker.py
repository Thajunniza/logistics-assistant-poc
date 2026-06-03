"""
Token usage tracker for the Logistics Assistant POC.

Captures every LLM call into a SQLite database with full attribution:
- WHO   made the call            (user_name)
- WHICH application               (application_name)
- WHICH agent                     (agent_name)
- WHICH model                     (model)
- HOW MUCH                        (prompt_tokens, completion_tokens, capacity_units, cost_eur)
- AGAINST WHICH risk              (risk_id)

PRICING MODEL — SAP Generative AI Hub
-------------------------------------
SAP Gen AI Hub bills in Capacity Units (CU). 1 CU = EUR 1.04/month at list price.

For gpt-4o, the SAP calculator reports:
    1,000 input tokens + 1,000 output tokens = 0.0235 CU per request

Splitting that into input/output components (using the standard 1:4 input:output
cost ratio for gpt-4o), we get the per-1K-token CU rates below. Edit PRICING to
reflect Aptiv's CPEA-discounted rates if available.
"""

from __future__ import annotations

import os
import sqlite3
import logging
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

DB_PATH = Path(os.getenv("TOKEN_DB_PATH", "./token_usage.db"))
DEFAULT_APP_NAME = os.getenv("APP_NAME", "logistics-assistant")

# -----------------------------------------------------------------------------
# Capacity-Unit pricing
# -----------------------------------------------------------------------------
# 1 CU = EUR 1.04/month at SAP list price.
# Override via env var if Aptiv has a discounted CU rate.
EUR_PER_CU = float(os.getenv("EUR_PER_CU", "1.04"))

# Per-model CU consumption per 1,000 tokens.
# Source: SAP Gen AI Hub in SAP AI Core Calculator
# (reference: gpt-4o 1K input + 1K output = 0.0235 CU per request).
PRICING = {
    "sap/gpt-4o": {
        "input_cu_per_1k":  0.0047,
        "output_cu_per_1k": 0.0188,
    },
    "sap/gpt-4o-mini": {
        # gpt-4o-mini is ~16x cheaper than gpt-4o per token; mirrored on CU.
        "input_cu_per_1k":  0.00028,
        "output_cu_per_1k": 0.00118,
    },
    # Add other models here as you adopt them.
}

DEFAULT_MODEL_FOR_PRICING = "sap/gpt-4o"


# -----------------------------------------------------------------------------
# Database setup
# -----------------------------------------------------------------------------

SCHEMA = """
CREATE TABLE IF NOT EXISTS llm_calls (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp_utc     TEXT NOT NULL,
    application_name  TEXT NOT NULL,
    user_name         TEXT NOT NULL,
    agent_name        TEXT NOT NULL,
    risk_id           TEXT,
    model             TEXT NOT NULL,
    prompt_tokens     INTEGER NOT NULL,
    completion_tokens INTEGER NOT NULL,
    total_tokens      INTEGER NOT NULL,
    capacity_units    REAL NOT NULL DEFAULT 0,
    cost_eur          REAL NOT NULL,
    latency_ms        INTEGER,
    success           INTEGER NOT NULL DEFAULT 1,
    error_message     TEXT
);

CREATE INDEX IF NOT EXISTS idx_llm_calls_timestamp ON llm_calls(timestamp_utc);
CREATE INDEX IF NOT EXISTS idx_llm_calls_agent     ON llm_calls(agent_name);
CREATE INDEX IF NOT EXISTS idx_llm_calls_user      ON llm_calls(user_name);
CREATE INDEX IF NOT EXISTS idx_llm_calls_app       ON llm_calls(application_name);
CREATE INDEX IF NOT EXISTS idx_llm_calls_risk      ON llm_calls(risk_id);
"""


@contextmanager
def get_conn():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _migrate_add_capacity_units(conn) -> None:
    """
    If the DB was created before capacity_units existed, add the column
    and back-fill it from existing token counts.
    """
    cur = conn.execute("PRAGMA table_info(llm_calls)")
    cols = {row["name"] for row in cur.fetchall()}
    if "capacity_units" not in cols:
        logger.info("Migrating: adding capacity_units column and back-filling.")
        conn.execute(
            "ALTER TABLE llm_calls ADD COLUMN capacity_units REAL NOT NULL DEFAULT 0"
        )
        rows = conn.execute(
            "SELECT id, model, prompt_tokens, completion_tokens FROM llm_calls"
        ).fetchall()
        for r in rows:
            cu = compute_capacity_units(r["model"], r["prompt_tokens"], r["completion_tokens"])
            conn.execute(
                "UPDATE llm_calls SET capacity_units = ? WHERE id = ?",
                (cu, r["id"]),
            )


def init_db():
    """Create the database and table if they don't exist, and run migrations."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_conn() as conn:
        conn.executescript(SCHEMA)
        _migrate_add_capacity_units(conn)
    logger.info("Token tracking DB ready at %s", DB_PATH)


# -----------------------------------------------------------------------------
# Cost calculation
# -----------------------------------------------------------------------------

def compute_capacity_units(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """CU consumed by one call, given token counts."""
    rates = PRICING.get(model) or PRICING[DEFAULT_MODEL_FOR_PRICING]
    cu_in  = (prompt_tokens / 1000.0)     * rates["input_cu_per_1k"]
    cu_out = (completion_tokens / 1000.0) * rates["output_cu_per_1k"]
    return round(cu_in + cu_out, 6)


def compute_cost_eur(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """EUR cost for one call: CU consumed × EUR per CU."""
    cu = compute_capacity_units(model, prompt_tokens, completion_tokens)
    return round(cu * EUR_PER_CU, 6)


# -----------------------------------------------------------------------------
# Recording
# -----------------------------------------------------------------------------

def record_call(
    agent_name: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    user_name: str = "system",
    application_name: str = DEFAULT_APP_NAME,
    risk_id: Optional[str] = None,
    latency_ms: Optional[int] = None,
    success: bool = True,
    error_message: Optional[str] = None,
) -> int:
    """
    Record one LLM call. Returns the new row ID, or -1 on tracking failure.

    Tracking failures NEVER raise — they only log — so a DB issue can't
    break agent execution.
    """
    try:
        total_tokens   = prompt_tokens + completion_tokens
        capacity_units = compute_capacity_units(model, prompt_tokens, completion_tokens)
        cost_eur       = round(capacity_units * EUR_PER_CU, 6)
        timestamp      = datetime.now(timezone.utc).isoformat()

        with get_conn() as conn:
            cur = conn.execute(
                """
                INSERT INTO llm_calls
                (timestamp_utc, application_name, user_name, agent_name, risk_id,
                 model, prompt_tokens, completion_tokens, total_tokens,
                 capacity_units, cost_eur,
                 latency_ms, success, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (timestamp, application_name, user_name, agent_name, risk_id,
                 model, prompt_tokens, completion_tokens, total_tokens,
                 capacity_units, cost_eur,
                 latency_ms, 1 if success else 0, error_message),
            )
            return cur.lastrowid
    except Exception as e:
        logger.error("Failed to record token usage: %s", e)
        return -1


# -----------------------------------------------------------------------------
# Helper to extract usage from LiteLLM response
# -----------------------------------------------------------------------------

def extract_usage_from_response(response) -> tuple[int, int]:
    """
    Pull (prompt_tokens, completion_tokens) from a LiteLLM response.
    Returns (0, 0) on any extraction problem — never raises.
    """
    try:
        usage = getattr(response, "usage", None)
        if usage is None:
            return (0, 0)
        prompt     = getattr(usage, "prompt_tokens", 0) or 0
        completion = getattr(usage, "completion_tokens", 0) or 0
        return (int(prompt), int(completion))
    except Exception as e:
        logger.warning("Could not extract token usage: %s", e)
        return (0, 0)


# -----------------------------------------------------------------------------
# Query helpers — backwards compatibility
# -----------------------------------------------------------------------------

def query_totals(application_name: Optional[str] = None):
    where = "WHERE success = 1"
    params = []
    if application_name:
        where += " AND application_name = ?"
        params.append(application_name)
    with get_conn() as conn:
        row = conn.execute(
            f"""
            SELECT
                COUNT(*)                            AS calls,
                COALESCE(SUM(prompt_tokens), 0)     AS input_tokens,
                COALESCE(SUM(completion_tokens), 0) AS output_tokens,
                COALESCE(SUM(total_tokens), 0)      AS total_tokens,
                COALESCE(SUM(capacity_units), 0.0)  AS capacity_units,
                COALESCE(SUM(cost_eur), 0.0)        AS cost_eur,
                COUNT(DISTINCT user_name)           AS unique_users
            FROM llm_calls
            {where}
            """,
            params,
        ).fetchone()
        return dict(row) if row else {}


def query_recent_calls(limit: int = 50, application_name: Optional[str] = None):
    where = ""
    params = []
    if application_name:
        where = "WHERE application_name = ?"
        params.append(application_name)
    params.append(limit)
    with get_conn() as conn:
        rows = conn.execute(
            f"""
            SELECT * FROM llm_calls
            {where}
            ORDER BY id DESC
            LIMIT ?
            """,
            params,
        ).fetchall()
        return [dict(r) for r in rows]
