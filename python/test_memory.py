"""
test_memory.py — Unit Tests for Disruption Memory System
=========================================================
Tests save/load/update/clear cycle, reflection context generation,
stats aggregation, and human override pattern detection.
Uses a temp file to avoid polluting real disruption_log.json.
"""

import os
import json
import pytest
import tempfile

# Patch MEMORY_FILE before importing memory module
_temp_dir = tempfile.mkdtemp()
_temp_memory_file = os.path.join(_temp_dir, "test_disruption_log.json")

import memory
memory.MEMORY_FILE = _temp_memory_file


# ---------------------------------------------------------------------------
# FIXTURES
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clean_memory():
    """Ensure each test starts with a clean memory file."""
    if os.path.exists(_temp_memory_file):
        os.remove(_temp_memory_file)
    yield
    if os.path.exists(_temp_memory_file):
        os.remove(_temp_memory_file)


SAMPLE_EVENT = {"event": "Port Strike", "location": "Rotterdam", "severity": "High"}
SAMPLE_RISK = {"urgency": "HIGH", "net_days_remaining": 2.5}
SAMPLE_STRATEGY = {"id": "SPLIT_ORDER", "name": "Split Order Strategy", "cost_premium_usd": 4000}


# ---------------------------------------------------------------------------
# CORE PERSISTENCE
# ---------------------------------------------------------------------------

class TestCorePersistence:

    def test_load_empty_returns_list(self):
        records = memory.load_memory()
        assert records == []

    def test_save_event_returns_id(self):
        rid = memory.save_event("AcmeMfg", SAMPLE_EVENT, SAMPLE_RISK, SAMPLE_STRATEGY)
        assert rid == 1

    def test_save_creates_file(self):
        memory.save_event("AcmeMfg", SAMPLE_EVENT, SAMPLE_RISK, SAMPLE_STRATEGY)
        assert os.path.exists(_temp_memory_file)

    def test_save_and_load_round_trip(self):
        memory.save_event("AcmeMfg", SAMPLE_EVENT, SAMPLE_RISK, SAMPLE_STRATEGY)
        records = memory.load_memory()
        assert len(records) == 1
        assert records[0]["company"] == "AcmeMfg"
        assert records[0]["event_type"] == "Port Strike"
        assert records[0]["strategy_id"] == "SPLIT_ORDER"
        assert records[0]["outcome"] == "pending"

    def test_sequential_ids(self):
        r1 = memory.save_event("A", SAMPLE_EVENT, SAMPLE_RISK, SAMPLE_STRATEGY)
        r2 = memory.save_event("B", SAMPLE_EVENT, SAMPLE_RISK, SAMPLE_STRATEGY)
        r3 = memory.save_event("C", SAMPLE_EVENT, SAMPLE_RISK, SAMPLE_STRATEGY)
        assert r1 == 1
        assert r2 == 2
        assert r3 == 3


# ---------------------------------------------------------------------------
# UPDATE OUTCOME
# ---------------------------------------------------------------------------

class TestUpdateOutcome:

    def test_update_existing_record(self):
        rid = memory.save_event("AcmeMfg", SAMPLE_EVENT, SAMPLE_RISK, SAMPLE_STRATEGY)
        success = memory.update_outcome(rid, "resolved")
        assert success is True
        records = memory.load_memory()
        assert records[0]["outcome"] == "resolved"
        assert "outcome_updated_at" in records[0]

    def test_update_nonexistent_record_returns_false(self):
        memory.save_event("AcmeMfg", SAMPLE_EVENT, SAMPLE_RISK, SAMPLE_STRATEGY)
        success = memory.update_outcome(999, "resolved")
        assert success is False

    def test_stockout_outcome(self):
        rid = memory.save_event("AcmeMfg", SAMPLE_EVENT, SAMPLE_RISK, SAMPLE_STRATEGY)
        memory.update_outcome(rid, "stockout_occurred")
        records = memory.load_memory()
        assert records[0]["outcome"] == "stockout_occurred"


# ---------------------------------------------------------------------------
# HUMAN OVERRIDE
# ---------------------------------------------------------------------------

class TestHumanOverride:

    def test_record_override(self):
        rid = memory.save_event("AcmeMfg", SAMPLE_EVENT, SAMPLE_RISK, SAMPLE_STRATEGY)
        success = memory.record_human_override(rid, "SPLIT_ORDER", "Too risky for our situation")
        assert success is True
        records = memory.load_memory()
        assert records[0]["human_override"] is True
        assert records[0]["original_strategy_id"] == "SPLIT_ORDER"
        assert records[0]["outcome"] == "overridden"

    def test_get_override_patterns(self):
        rid = memory.save_event("A", SAMPLE_EVENT, SAMPLE_RISK, SAMPLE_STRATEGY)
        memory.record_human_override(rid, "SPLIT_ORDER", "Not suitable")
        patterns = memory.get_override_patterns()
        assert len(patterns) == 1
        assert patterns[0]["strategy_id"] == "SPLIT_ORDER"
        assert patterns[0]["override_count"] == 1


# ---------------------------------------------------------------------------
# CLEAR MEMORY
# ---------------------------------------------------------------------------

class TestClearMemory:

    def test_clear_removes_file(self):
        memory.save_event("AcmeMfg", SAMPLE_EVENT, SAMPLE_RISK, SAMPLE_STRATEGY)
        assert os.path.exists(_temp_memory_file)
        memory.clear_memory()
        assert not os.path.exists(_temp_memory_file)

    def test_clear_on_empty_is_safe(self):
        memory.clear_memory()  # Should not raise


# ---------------------------------------------------------------------------
# STATS
# ---------------------------------------------------------------------------

class TestStats:

    def test_empty_stats(self):
        stats = memory.get_stats()
        assert stats["total_events"] == 0
        assert stats["resolved"] == 0
        assert stats["success_rate_pct"] == 0

    def test_stats_with_mixed_outcomes(self):
        r1 = memory.save_event("A", SAMPLE_EVENT, SAMPLE_RISK, SAMPLE_STRATEGY)
        r2 = memory.save_event("B", SAMPLE_EVENT, SAMPLE_RISK, SAMPLE_STRATEGY)
        r3 = memory.save_event("C", SAMPLE_EVENT, SAMPLE_RISK, SAMPLE_STRATEGY)
        memory.update_outcome(r1, "resolved")
        memory.update_outcome(r2, "resolved")
        memory.update_outcome(r3, "stockout_occurred")
        stats = memory.get_stats()
        assert stats["total_events"] == 3
        assert stats["resolved"] == 2
        assert stats["stockouts"] == 1
        assert stats["success_rate_pct"] == 67  # 2/3 rounded

    def test_total_cost_premium(self):
        memory.save_event("A", SAMPLE_EVENT, SAMPLE_RISK, {"id": "X", "name": "X", "cost_premium_usd": 1000})
        memory.save_event("B", SAMPLE_EVENT, SAMPLE_RISK, {"id": "Y", "name": "Y", "cost_premium_usd": 2500})
        stats = memory.get_stats()
        assert stats["total_cost_premium_usd"] == 3500


# ---------------------------------------------------------------------------
# REFLECTION CONTEXT
# ---------------------------------------------------------------------------

class TestReflectionContext:

    def test_no_history_returns_default_message(self):
        ctx = memory.get_reflection_context("AcmeMfg")
        assert "No past disruption history" in ctx
        assert "conservative defaults" in ctx

    def test_with_history_returns_formatted_context(self):
        r1 = memory.save_event("AcmeMfg", SAMPLE_EVENT, SAMPLE_RISK, SAMPLE_STRATEGY)
        memory.update_outcome(r1, "resolved")
        ctx = memory.get_reflection_context("AcmeMfg")
        assert "Historical disruption memory" in ctx
        assert "SPLIT_ORDER" in ctx
        assert "✓" in ctx  # resolved icon

    def test_stockout_learning_signal(self):
        r1 = memory.save_event("AcmeMfg", SAMPLE_EVENT, SAMPLE_RISK, SAMPLE_STRATEGY)
        memory.update_outcome(r1, "stockout_occurred")
        ctx = memory.get_reflection_context("AcmeMfg")
        assert "LEARNING SIGNAL" in ctx
        assert "stockouts" in ctx.lower()

    def test_filters_by_company(self):
        memory.save_event("AcmeMfg", SAMPLE_EVENT, SAMPLE_RISK, SAMPLE_STRATEGY)
        memory.save_event("TexMex", SAMPLE_EVENT, SAMPLE_RISK, SAMPLE_STRATEGY)
        ctx = memory.get_reflection_context("AcmeMfg")
        assert "1 total events" in ctx
