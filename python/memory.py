"""
memory.py — Disruption Memory & Reflection System
===================================================
Implements the "Memory & Reflection" requirement from the case package.

Persists every disruption event and agent decision to a local JSON file.
Before each new analysis, the agent reads this history and uses it to:
  - Avoid repeating failed strategies
  - Detect recurring suppliers/routes as systemic risks
  - Improve confidence scoring over time

Storage: disruption_log.json (same directory as this file)
"""

import json
import os
from datetime import datetime

MEMORY_FILE = os.path.join(os.path.dirname(__file__), "disruption_log.json")


# ---------------------------------------------------------------------------
# CORE PERSISTENCE
# ---------------------------------------------------------------------------

def load_memory() -> list[dict]:
    """Load all past disruption records. Returns empty list if no file yet."""
    if not os.path.exists(MEMORY_FILE):
        return []
    try:
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def _save_memory(records: list[dict]) -> None:
    with open(MEMORY_FILE, "w") as f:
        json.dump(records, f, indent=2)


def save_event(
    company: str,
    event: dict,
    risk: dict,
    strategy: dict,
    outcome: str = "pending",
) -> int:
    """
    Append a new disruption record to the log.

    Args:
        company:  Company profile name (e.g. "AcmeMfg GmbH")
        event:    The disruption event dict (type, location, severity)
        risk:     The risk assessment dict (urgency, net_days_remaining)
        strategy: The chosen_strategy dict from Gemini
        outcome:  "pending" | "resolved" | "stockout_occurred"

    Returns:
        The integer ID of the saved record.
    """
    records = load_memory()
    record_id = len(records) + 1
    records.append({
        "id": record_id,
        "timestamp": datetime.now().isoformat(),
        "company": company,
        "event_type": event.get("event", "Unknown"),
        "event_location": event.get("location", "Unknown"),
        "severity": event.get("severity", "Unknown"),
        "risk_urgency": risk.get("urgency", "UNKNOWN"),
        "net_days_remaining": risk.get("net_days_remaining", 0),
        "strategy_id": strategy.get("id", "UNKNOWN"),
        "strategy_name": strategy.get("name", "Unknown"),
        "cost_premium_usd": strategy.get("cost_premium_usd", 0),
        "outcome": outcome,
    })
    _save_memory(records)
    return record_id


def update_outcome(record_id: int, outcome: str) -> bool:
    """
    Update the outcome of a past event (called after manager approves/rejects
    and later marks the situation as resolved or as a stockout).

    Args:
        record_id: The ID returned by save_event().
        outcome:   "resolved" | "stockout_occurred" | "pending"

    Returns:
        True if the record was found and updated, False otherwise.
    """
    records = load_memory()
    for record in records:
        if record["id"] == record_id:
            record["outcome"] = outcome
            record["outcome_updated_at"] = datetime.now().isoformat()
            _save_memory(records)
            return True
    return False


def record_human_override(record_id: int, original_strategy_id: str, override_reason: str) -> bool:
    """
    Log when a human overrides the agent's recommended strategy.
    This creates a learning signal: the agent will see which strategies
    humans rejected and why, improving future recommendations.

    Args:
        record_id:           The ID returned by save_event().
        original_strategy_id: The strategy the agent recommended.
        override_reason:     Free-text reason from the human operator.

    Returns:
        True if the record was found and updated, False otherwise.
    """
    records = load_memory()
    for record in records:
        if record["id"] == record_id:
            record["human_override"] = True
            record["original_strategy_id"] = original_strategy_id
            record["override_reason"] = override_reason
            record["override_at"] = datetime.now().isoformat()
            record["outcome"] = "overridden"
            _save_memory(records)
            return True
    return False


def get_override_patterns() -> list[dict]:
    """
    Return strategies that humans have repeatedly overridden.
    Injected into the Gemini prompt as a caution signal.
    """
    records = load_memory()
    overrides = [r for r in records if r.get("human_override")]
    from collections import Counter
    counts = Counter(r["strategy_id"] for r in overrides)
    return [{"strategy_id": sid, "override_count": cnt, "sample_reason": next(
        r.get("override_reason", "") for r in overrides if r["strategy_id"] == sid
    )} for sid, cnt in counts.most_common()]


def clear_memory() -> None:
    """Wipe the disruption log. Use with care — for demo reset only."""
    if os.path.exists(MEMORY_FILE):
        os.remove(MEMORY_FILE)


# ---------------------------------------------------------------------------
# ANALYTICS
# ---------------------------------------------------------------------------

def get_stats() -> dict:
    """
    Compute high-level statistics across all logged disruptions.
    Used to populate the Memory dashboard in the Streamlit UI.
    """
    records = load_memory()
    if not records:
        return {
            "total_events": 0,
            "resolved": 0,
            "stockouts": 0,
            "pending": 0,
            "success_rate_pct": 0,
            "total_cost_premium_usd": 0,
            "most_common_event": "—",
            "most_affected_location": "—",
        }

    resolved  = sum(1 for r in records if r["outcome"] == "resolved")
    stockouts = sum(1 for r in records if r["outcome"] == "stockout_occurred")
    pending   = sum(1 for r in records if r["outcome"] == "pending")
    decided   = resolved + stockouts

    from collections import Counter
    event_counts    = Counter(r["event_type"]     for r in records)
    location_counts = Counter(r["event_location"] for r in records)

    return {
        "total_events":          len(records),
        "resolved":              resolved,
        "stockouts":             stockouts,
        "pending":               pending,
        "success_rate_pct":      round(resolved / decided * 100) if decided else 0,
        "total_cost_premium_usd": sum(r.get("cost_premium_usd", 0) for r in records),
        "most_common_event":     event_counts.most_common(1)[0][0] if event_counts else "—",
        "most_affected_location": location_counts.most_common(1)[0][0] if location_counts else "—",
    }


# ---------------------------------------------------------------------------
# REFLECTION CONTEXT (injected into the Gemini prompt)
# ---------------------------------------------------------------------------

def get_reflection_context(company: str | None = None) -> str:
    """
    Return a formatted string of past disruption decisions for inclusion in
    the Gemini prompt. Filters by company if provided.

    The agent uses this to:
      1. Avoid strategies that previously led to stockouts.
      2. Note if a supplier/route has been problematic before.
      3. Increase confidence when a strategy has a strong track record.
    """
    records = load_memory()
    if company:
        records = [r for r in records if r.get("company") == company]

    if not records:
        return (
            "No past disruption history available for this company. "
            "This is the first recorded event — apply conservative defaults."
        )

    recent = records[-5:]  # last 5 events
    lines = [f"Historical disruption memory ({len(records)} total events, showing last {len(recent)}):"]

    for r in reversed(recent):  # newest first
        outcome_icon = {"resolved": "✓", "stockout_occurred": "✗ STOCKOUT", "pending": "⏳"}.get(
            r["outcome"], "?"
        )
        lines.append(
            f"  [{r['timestamp'][:10]}] {r['event_type']} @ {r['event_location']} "
            f"[{r['severity']}] → Strategy: {r['strategy_id']} "
            f"(cost: ${r.get('cost_premium_usd', 0):,}) → Outcome: {outcome_icon}"
        )

    # Derive insights for the agent
    stockout_strategies = {r["strategy_id"] for r in records if r["outcome"] == "stockout_occurred"}
    if stockout_strategies:
        lines.append(
            f"\n⚠ LEARNING SIGNAL: The following strategies previously resulted in stockouts "
            f"for this company — avoid if possible: {', '.join(stockout_strategies)}"
        )

    resolved_strategies = {r["strategy_id"] for r in records if r["outcome"] == "resolved"}
    if resolved_strategies:
        lines.append(
            f"✓ LEARNING SIGNAL: The following strategies have a proven success record: "
            f"{', '.join(resolved_strategies)}"
        )

    return "\n".join(lines)
