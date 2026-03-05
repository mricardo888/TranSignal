"""
test_erp_data.py — Unit Tests for ERP Profile Data
====================================================
Tests buffer day calculations, supplier dataframe generation,
and structural integrity of both company profiles.
"""

import pytest
from erp_data import (
    ERP_PROFILES,
    get_inventory_buffer_days,
    get_suppliers_as_dataframe_rows,
)


# ---------------------------------------------------------------------------
# PROFILE STRUCTURAL INTEGRITY
# ---------------------------------------------------------------------------

REQUIRED_TOP_KEYS = {
    "company", "product", "profile_type", "risk_appetite",
    "concentration_risk", "inventory", "suppliers", "warehouse",
    "sla", "auto_alerts", "map_view",
}

REQUIRED_SUPPLIER_KEYS = {
    "id", "name", "city", "country", "lat", "lon",
    "normal_lead_time_days", "unit_cost_usd", "active_po_units",
    "transit_hub", "contact_email", "role", "color",
}

REQUIRED_SLA_KEYS = {
    "max_acceptable_delay_days", "daily_production_value_usd",
    "key_customer", "autonomous_action_limit_usd",
}


class TestProfileStructure:
    """Verify both ERP profiles contain all required keys."""

    @pytest.mark.parametrize("profile_name", list(ERP_PROFILES.keys()))
    def test_has_required_top_keys(self, profile_name):
        profile = ERP_PROFILES[profile_name]
        missing = REQUIRED_TOP_KEYS - set(profile.keys())
        assert not missing, f"Profile '{profile_name}' missing keys: {missing}"

    @pytest.mark.parametrize("profile_name", list(ERP_PROFILES.keys()))
    def test_has_three_suppliers(self, profile_name):
        profile = ERP_PROFILES[profile_name]
        assert "primary" in profile["suppliers"]
        assert "secondary" in profile["suppliers"]
        assert "tertiary" in profile["suppliers"]

    @pytest.mark.parametrize("profile_name", list(ERP_PROFILES.keys()))
    def test_supplier_keys_complete(self, profile_name):
        profile = ERP_PROFILES[profile_name]
        for role, sup in profile["suppliers"].items():
            missing = REQUIRED_SUPPLIER_KEYS - set(sup.keys())
            assert not missing, f"Supplier '{role}' in '{profile_name}' missing: {missing}"

    @pytest.mark.parametrize("profile_name", list(ERP_PROFILES.keys()))
    def test_sla_keys_complete(self, profile_name):
        profile = ERP_PROFILES[profile_name]
        missing = REQUIRED_SLA_KEYS - set(profile["sla"].keys())
        assert not missing, f"SLA in '{profile_name}' missing keys: {missing}"

    @pytest.mark.parametrize("profile_name", list(ERP_PROFILES.keys()))
    def test_auto_alerts_non_empty(self, profile_name):
        profile = ERP_PROFILES[profile_name]
        assert len(profile["auto_alerts"]) > 0, "auto_alerts should not be empty"

    @pytest.mark.parametrize("profile_name", list(ERP_PROFILES.keys()))
    def test_auto_alerts_have_wider_types(self, profile_name):
        """Verify each profile has the expanded disruption types."""
        profile = ERP_PROFILES[profile_name]
        event_types = {a["event"] for a in profile["auto_alerts"]}
        wider_types = {"Semiconductor Shortage", "Supplier Insolvency", "Geopolitical Sanctions",
                       "Port Congestion", "Raw Material Price Spike", "Regulatory Change"}
        missing = wider_types - event_types
        assert not missing, f"Profile '{profile_name}' missing wider disruption types: {missing}"


# ---------------------------------------------------------------------------
# INVENTORY BUFFER DAYS
# ---------------------------------------------------------------------------

class TestBufferDays:

    def test_acme_buffer_days(self):
        """AcmeMfg: 500 units ÷ 50 units/day = 10.0 days."""
        acme = list(ERP_PROFILES.values())[0]
        buf = get_inventory_buffer_days(acme)
        assert buf == 10.0

    def test_texmex_buffer_days(self):
        """TexMex: 3000 units ÷ 300 units/day = 10.0 days."""
        texmex = list(ERP_PROFILES.values())[1]
        buf = get_inventory_buffer_days(texmex)
        assert buf == 10.0

    def test_custom_erp_data(self):
        custom = {
            "inventory": {"on_hand_units": 200, "burn_rate_per_day": 20, "safety_stock_days": 2, "reorder_point_units": 50}
        }
        buf = get_inventory_buffer_days(custom)
        assert buf == 10.0

    def test_high_burn_rate(self):
        custom = {
            "inventory": {"on_hand_units": 100, "burn_rate_per_day": 100, "safety_stock_days": 1, "reorder_point_units": 50}
        }
        buf = get_inventory_buffer_days(custom)
        assert buf == 1.0


# ---------------------------------------------------------------------------
# SUPPLIER DATAFRAME ROWS
# ---------------------------------------------------------------------------

class TestSupplierDataframe:

    @pytest.mark.parametrize("profile_name", list(ERP_PROFILES.keys()))
    def test_returns_four_rows(self, profile_name):
        """3 suppliers + 1 warehouse = 4 rows."""
        profile = ERP_PROFILES[profile_name]
        rows = get_suppliers_as_dataframe_rows(profile)
        assert len(rows) == 4

    @pytest.mark.parametrize("profile_name", list(ERP_PROFILES.keys()))
    def test_rows_have_required_fields(self, profile_name):
        profile = ERP_PROFILES[profile_name]
        rows = get_suppliers_as_dataframe_rows(profile)
        for row in rows:
            assert "name" in row
            assert "role" in row
            assert "lat" in row
            assert "lon" in row
            assert "color" in row

    @pytest.mark.parametrize("profile_name", list(ERP_PROFILES.keys()))
    def test_warehouse_row_present(self, profile_name):
        profile = ERP_PROFILES[profile_name]
        rows = get_suppliers_as_dataframe_rows(profile)
        roles = [r["role"] for r in rows]
        assert "Warehouse" in roles

    @pytest.mark.parametrize("profile_name", list(ERP_PROFILES.keys()))
    def test_coordinates_are_valid(self, profile_name):
        profile = ERP_PROFILES[profile_name]
        rows = get_suppliers_as_dataframe_rows(profile)
        for row in rows:
            assert -90 <= row["lat"] <= 90, f"Invalid lat: {row['lat']}"
            assert -180 <= row["lon"] <= 180, f"Invalid lon: {row['lon']}"
