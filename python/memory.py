"""
memory.py — Disruption Memory & Reflection System
===================================================
Implements the "Memory & Reflection" requirement from the case package.

Persists every disruption event and agent decision.
Uses Google Firebase Firestore if FIREBASE_CREDENTIALS is set.
Otherwise, falls back to local disruption_log.json.
"""

import json
import os
from datetime import datetime
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore

MEMORY_FILE = os.path.join(os.path.dirname(__file__), "disruption_log.json")

# --- Initialise env vars locally ---
_here = os.path.dirname(os.path.abspath(__file__))
_root = os.path.dirname(_here)
load_dotenv(os.path.join(_here, ".env"))
load_dotenv(os.path.join(_root, ".env"))

# --- Firebase Initialization ---
USE_FIREBASE = False
db = None

# Attempt to load from JSON string in env var, or file path in env var
fb_creds_env = os.environ.get("FIREBASE_CREDENTIALS")
if fb_creds_env:
    try:
        # Check if it's a JSON string
        if fb_creds_env.strip().startswith("{"):
            cred_dict = json.loads(fb_creds_env)
            cred = credentials.Certificate(cred_dict)
        else:
            # Assume it's a file path. E.g if "./key.json", we must make it absolute relative to this file
            if not os.path.isabs(fb_creds_env):
                fb_creds_env = os.path.join(_here, fb_creds_env)
            cred = credentials.Certificate(fb_creds_env)
        
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred)
        db = firestore.client()
        USE_FIREBASE = True
        print("[MEMORY] ✅ Connected to Google Firebase Firestore.")
    except Exception as e:
        print(f"[MEMORY] ⚠️ Failed to initialize Firebase: {e}. Falling back to local JSON.")
        USE_FIREBASE = False
else:
    print("[MEMORY] ℹ️ No FIREBASE_CREDENTIALS found. Using local JSON for memory.")

# ---------------------------------------------------------------------------
# CORE PERSISTENCE
# ---------------------------------------------------------------------------

def load_memory() -> list[dict]:
    """Load all past disruption records from Firebase or JSON file."""
    if USE_FIREBASE:
        try:
            docs = db.collection("disruption_events").order_by("timestamp").stream()
            records = [doc.to_dict() for doc in docs]
            return records
        except Exception as e:
            print(f"[MEMORY] Firebase read error: {e}")
            return []
    else:
        if not os.path.exists(MEMORY_FILE):
            return []
        try:
            with open(MEMORY_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []


def _save_memory_local(records: list[dict]) -> None:
    with open(MEMORY_FILE, "w") as f:
        json.dump(records, f, indent=2)


def save_event(
    company: str,
    event: dict,
    risk: dict,
    strategy: dict,
    outcome: str = "pending",
) -> str:
    """Append a new disruption record to the log (Firebase or JSON)."""
    records = load_memory()
    # Generate generic ID
    record_id = str(len(records) + 1)
    
    new_record = {
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
    }
    
    if USE_FIREBASE:
        db.collection("disruption_events").document(record_id).set(new_record)
    else:
        records.append(new_record)
        _save_memory_local(records)
        
    return record_id


def update_outcome(record_id: str, outcome: str) -> bool:
    if USE_FIREBASE:
        doc_ref = db.collection("disruption_events").document(str(record_id))
        doc = doc_ref.get()
        if doc.exists:
            doc_ref.update({
                "outcome": outcome,
                "outcome_updated_at": datetime.now().isoformat()
            })
            return True
        return False
    else:
        records = load_memory()
        for record in records:
            if str(record["id"]) == str(record_id):
                record["outcome"] = outcome
                record["outcome_updated_at"] = datetime.now().isoformat()
                _save_memory_local(records)
                return True
        return False


def record_human_override(record_id: str, original_strategy_id: str, override_reason: str) -> bool:
    if USE_FIREBASE:
        doc_ref = db.collection("disruption_events").document(str(record_id))
        if doc_ref.get().exists:
            doc_ref.update({
                "human_override": True,
                "original_strategy_id": original_strategy_id,
                "override_reason": override_reason,
                "override_at": datetime.now().isoformat(),
                "outcome": "overridden"
            })
            return True
        return False
    else:
        records = load_memory()
        for record in records:
            if str(record["id"]) == str(record_id):
                record["human_override"] = True
                record["original_strategy_id"] = original_strategy_id
                record["override_reason"] = override_reason
                record["override_at"] = datetime.now().isoformat()
                record["outcome"] = "overridden"
                _save_memory_local(records)
                return True
        return False


def get_override_patterns() -> list[dict]:
    records = load_memory()
    overrides = [r for r in records if r.get("human_override")]
    from collections import Counter
    counts = Counter(r["strategy_id"] for r in overrides)
    return [{"strategy_id": sid, "override_count": cnt, "sample_reason": next(
        r.get("override_reason", "") for r in overrides if r["strategy_id"] == sid
    )} for sid, cnt in counts.most_common()]


def clear_memory() -> None:
    if USE_FIREBASE:
        # Delete all documents in collection
        docs = db.collection("disruption_events").stream()
        for doc in docs:
            doc.reference.delete()
    else:
        if os.path.exists(MEMORY_FILE):
            os.remove(MEMORY_FILE)


# ---------------------------------------------------------------------------
# ANALYTICS & REFLECTION CONTEXT
# ---------------------------------------------------------------------------

def get_stats() -> dict:
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

def get_reflection_context(company: str | None = None) -> str:
    records = load_memory()
    if company:
        records = [r for r in records if r.get("company") == company]

    if not records:
        return (
            "No past disruption history available for this company. "
            "This is the first recorded event — apply conservative defaults."
        )

    recent = records[-5:]
    lines = [f"Historical disruption memory ({len(records)} total events, showing last {len(recent)}):"]

    for r in reversed(recent):
        outcome_icon = {"resolved": "✓", "stockout_occurred": "✗ STOCKOUT", "pending": "⏳"}.get(
            r["outcome"], "?"
        )
        lines.append(
            f"  [{r['timestamp'][:10]}] {r['event_type']} @ {r['event_location']} "
            f"[{r['severity']}] → Strategy: {r['strategy_id']} "
            f"(cost: ${r.get('cost_premium_usd', 0):,}) → Outcome: {outcome_icon}"
        )

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
