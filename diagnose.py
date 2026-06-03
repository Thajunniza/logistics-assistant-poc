"""
Diagnostic: why are first LLM attempts failing and needing repair retries?

Run from your project root:
    python diagnose_retries.py

This reads your existing token_usage.db and answers:
- Which agents retry most often?
- Are failures near the max_tokens cap (= truncation) or well under (= schema mismatch)?
- What does the error message say?
"""

import sqlite3
from pathlib import Path
from collections import defaultdict

DB_PATH = Path("token_usage.db")

if not DB_PATH.exists():
    print(f"No database found at {DB_PATH.resolve()}")
    print("Make sure you run this from the project root.")
    raise SystemExit(1)

conn = sqlite3.connect(str(DB_PATH))
conn.row_factory = sqlite3.Row

# Pull every call
rows = conn.execute(
    """
    SELECT id, timestamp_utc, agent_name, model,
           prompt_tokens, completion_tokens, success, error_message
    FROM llm_calls
    ORDER BY id ASC
    """
).fetchall()

if not rows:
    print("No LLM calls recorded yet.")
    raise SystemExit(0)

print(f"Loaded {len(rows)} call records.\n")

# -----------------------------------------------------------------------------
# Group calls into logical pairs (first attempt + repair retry on same agent)
# -----------------------------------------------------------------------------
# Heuristic: a row whose agent_name ends with "[repair-retry]" is the retry
# of the *previous* row for the same logical agent.

retries_by_agent = defaultdict(lambda: {"total_first": 0, "retried": 0, "retry_succeeded": 0})
truncation_suspects = []
schema_mismatch_suspects = []

i = 0
while i < len(rows):
    row = rows[i]
    name = row["agent_name"]

    if "[repair-retry]" in name:
        # This shouldn't be the first record we see; skip
        i += 1
        continue

    base_name = name
    retries_by_agent[base_name]["total_first"] += 1

    # Was the next row a repair retry for this agent?
    if i + 1 < len(rows):
        next_row = rows[i + 1]
        if (next_row["agent_name"].startswith(base_name) and
                "[repair-retry]" in next_row["agent_name"]):
            retries_by_agent[base_name]["retried"] += 1
            if next_row["success"] == 1:
                retries_by_agent[base_name]["retry_succeeded"] += 1

            # First-attempt token diagnosis
            first_completion = row["completion_tokens"] or 0
            if first_completion >= 800:
                truncation_suspects.append({
                    "id": row["id"],
                    "agent": base_name,
                    "completion_tokens": first_completion,
                    "error": (row["error_message"] or "")[:120],
                })
            elif first_completion > 0:
                schema_mismatch_suspects.append({
                    "id": row["id"],
                    "agent": base_name,
                    "completion_tokens": first_completion,
                    "error": (row["error_message"] or "")[:120],
                })
            i += 2
            continue
    i += 1

# -----------------------------------------------------------------------------
# Report
# -----------------------------------------------------------------------------
print("=" * 70)
print("RETRY RATE BY AGENT")
print("=" * 70)
print(f"{'Agent':<40} {'First':>6} {'Retried':>8} {'Rate':>7} {'Recovered':>10}")
for agent, stats in sorted(retries_by_agent.items(),
                            key=lambda kv: -kv[1]["retried"]):
    total = stats["total_first"]
    retried = stats["retried"]
    rate = (retried / total * 100) if total else 0
    rec = (stats["retry_succeeded"] / retried * 100) if retried else 0
    print(f"  {agent:<38} {total:>6} {retried:>8} {rate:>6.1f}% {rec:>9.1f}%")

print()
overall_first = sum(s["total_first"] for s in retries_by_agent.values())
overall_retried = sum(s["retried"] for s in retries_by_agent.values())
overall_rate = (overall_retried / overall_first * 100) if overall_first else 0
print(f"OVERALL: {overall_retried}/{overall_first} first attempts retried = {overall_rate:.1f}%")
print()

# -----------------------------------------------------------------------------
# Diagnosis
# -----------------------------------------------------------------------------
print("=" * 70)
print("LIKELY ROOT CAUSE")
print("=" * 70)

n_trunc = len(truncation_suspects)
n_schema = len(schema_mismatch_suspects)

if n_trunc > 0 and n_trunc >= n_schema:
    print(f"\n>>> TRUNCATION suspected ({n_trunc} cases)")
    print("    First-attempt completion_tokens are >= 800 (close to typical max_tokens=900).")
    print("    The model is being cut off mid-JSON.")
    print()
    print("    FIX: increase max_tokens in client.py.")
    print("    For agents with rich structured output (Inventory Supervisor especially),")
    print("    try max_tokens=2000 or 3000.")
    print()
    print("    Examples:")
    for s in truncation_suspects[:5]:
        print(f"      id={s['id']:>4}  {s['agent']:<35}  {s['completion_tokens']} tokens out")

if n_schema > 0 and n_schema > n_trunc:
    print(f"\n>>> SCHEMA MISMATCH suspected ({n_schema} cases)")
    print("    First-attempt completion_tokens are well under max_tokens cap.")
    print("    The model returned JSON but it doesn't match your Pydantic schema.")
    print()
    print("    LIKELY FIXES (in order of impact):")
    print("    1. Pass response_format={'type': 'json_object'} in litellm.completion()")
    print("       — forces the API to return parseable JSON.")
    print("    2. Include the JSON schema in the system prompt.")
    print("       — agents need to see exactly what fields you expect.")
    print("    3. Use litellm.completion(..., response_format=YourPydanticModel)")
    print("       — newer LiteLLM versions support direct Pydantic-as-schema.")
    print()
    print("    Examples:")
    for s in schema_mismatch_suspects[:5]:
        print(f"      id={s['id']:>4}  {s['agent']:<35}  {s['completion_tokens']} tokens out")

if overall_rate > 50:
    print()
    print("    NOTE: retry rate is > 50%. This is structural — fix at the call level,")
    print("    not per-agent. Almost certainly missing response_format JSON-mode.")

# -----------------------------------------------------------------------------
# Sample error messages
# -----------------------------------------------------------------------------
print()
print("=" * 70)
print("SAMPLE ERROR MESSAGES FROM FAILED FIRST ATTEMPTS")
print("=" * 70)
err_samples = conn.execute(
    """
    SELECT agent_name, error_message, COUNT(*) as cnt
    FROM llm_calls
    WHERE success = 0 AND error_message IS NOT NULL
      AND agent_name NOT LIKE '%[repair-retry]%'
    GROUP BY error_message
    ORDER BY cnt DESC
    LIMIT 5
    """
).fetchall()
if err_samples:
    for s in err_samples:
        print(f"  [{s['cnt']}x] {s['agent_name']}")
        print(f"         {(s['error_message'] or '')[:200]}")
        print()
else:
    print("  No error messages recorded.")

conn.close()