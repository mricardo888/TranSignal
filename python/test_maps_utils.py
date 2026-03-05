"""
test_maps_utils.py — Unit Tests for Geospatial Layer
=====================================================
Tests Haversine distance, geocoding cache, transit delay model,
and stockout risk classification.
"""

import pytest
from maps_utils import (
    haversine_km,
    geocode_location,
    get_transit_delay,
    assess_stockout_risk,
    CITY_COORDS,
    SEVERITY_MULTIPLIER,
)


# ---------------------------------------------------------------------------
# HAVERSINE DISTANCE
# ---------------------------------------------------------------------------

class TestHaversine:
    """Test the Haversine great-circle distance formula."""

    def test_same_point_returns_zero(self):
        assert haversine_km(51.9244, 4.4777, 51.9244, 4.4777) == 0.0

    def test_rotterdam_to_paris_within_range(self):
        """Rotterdam → Paris is ~370 km; Haversine should be close."""
        dist = haversine_km(51.9244, 4.4777, 48.8566, 2.3522)
        assert 350 < dist < 400, f"Expected ~370 km, got {dist} km"

    def test_new_york_to_london_within_range(self):
        """Transatlantic distance should be ~5,500 km."""
        dist = haversine_km(40.7128, -74.0060, 51.5074, -0.1278)
        assert 5400 < dist < 5700, f"Expected ~5,570 km, got {dist} km"

    def test_symmetry(self):
        """Distance A→B should equal B→A."""
        d1 = haversine_km(48.8566, 2.3522, 35.6762, 139.6503)
        d2 = haversine_km(35.6762, 139.6503, 48.8566, 2.3522)
        assert abs(d1 - d2) < 0.01

    def test_monterrey_to_houston_is_short_haul(self):
        """Monterrey → Houston is ~500 km, should classify as road freight."""
        dist = haversine_km(25.6866, -100.3161, 29.7604, -95.3698)
        assert dist < 1500, f"Expected short-haul (<1500 km), got {dist} km"


# ---------------------------------------------------------------------------
# GEOCODING (cache hits)
# ---------------------------------------------------------------------------

class TestGeocode:
    """Test the geocode_location function with cached cities."""

    def test_cached_city_returns_correct_coords(self):
        result = geocode_location("Rotterdam")
        assert result["source"] == "cache"
        assert not result["_is_mock"]
        assert abs(result["location"]["lat"] - 51.9244) < 0.01
        assert abs(result["location"]["lng"] - 4.4777) < 0.01

    def test_case_insensitive_lookup(self):
        result = geocode_location("SHANGHAI")
        assert result["source"] == "cache"
        assert abs(result["location"]["lat"] - 31.2304) < 0.01

    def test_new_cities_in_cache(self):
        """Verify the newly added wider-disruption cities exist."""
        new_cities = ["taipei", "detroit", "suez", "piraeus", "hsinchu", "dresden"]
        for city in new_cities:
            assert city in CITY_COORDS, f"{city} missing from CITY_COORDS"

    def test_unknown_location_returns_fallback(self):
        """Unknown cities without Nominatim should return fallback."""
        # This test may hit Nominatim; if so, it still passes
        result = geocode_location("xyznonexistentcity12345")
        # Should either find via Nominatim or return fallback
        assert "location" in result
        assert "lat" in result["location"]


# ---------------------------------------------------------------------------
# TRANSIT DELAY MODEL
# ---------------------------------------------------------------------------

class TestTransitDelay:
    """Test the transit delay calculation pipeline."""

    def test_returns_valid_structure(self):
        result = get_transit_delay("Rotterdam", "Paris, France", "High")
        assert "distance_km" in result
        assert "normal_duration_hours" in result
        assert "disrupted_duration_hours" in result
        assert "delay_added_days" in result
        assert result["distance_km"] > 0

    def test_severity_multipliers_applied(self):
        low = get_transit_delay("Rotterdam", "Paris, France", "Low")
        high = get_transit_delay("Rotterdam", "Paris, France", "High")
        critical = get_transit_delay("Rotterdam", "Paris, France", "Critical")
        assert low["disrupted_duration_hours"] < high["disrupted_duration_hours"]
        assert high["disrupted_duration_hours"] < critical["disrupted_duration_hours"]

    def test_all_severity_levels_exist(self):
        for sev in ["Low", "Medium", "High", "Critical"]:
            assert sev in SEVERITY_MULTIPLIER

    def test_short_haul_uses_road_model(self):
        result = get_transit_delay("Monterrey", "Houston", "High")
        assert "road" in result["method"].lower()

    def test_long_haul_uses_sea_model(self):
        result = get_transit_delay("Shanghai", "Rotterdam", "High")
        assert "sea" in result["method"].lower()


# ---------------------------------------------------------------------------
# STOCKOUT RISK ASSESSMENT
# ---------------------------------------------------------------------------

class TestStockoutRisk:
    """Test the assess_stockout_risk urgency classifier."""

    def test_critical_when_net_negative(self):
        result = assess_stockout_risk(delay_days=15, buffer_days=10, safety_stock_days=3)
        assert result["urgency"] == "CRITICAL"
        assert result["stockout_will_occur"] is True

    def test_high_when_below_safety(self):
        result = assess_stockout_risk(delay_days=8, buffer_days=10, safety_stock_days=3)
        assert result["urgency"] == "HIGH"
        assert result["stockout_will_occur"] is True

    def test_medium_when_within_double_safety(self):
        result = assess_stockout_risk(delay_days=5, buffer_days=10, safety_stock_days=3)
        assert result["urgency"] == "MEDIUM"
        assert result["stockout_will_occur"] is False

    def test_low_when_ample_buffer(self):
        result = assess_stockout_risk(delay_days=1, buffer_days=10, safety_stock_days=3)
        assert result["urgency"] == "LOW"
        assert result["stockout_will_occur"] is False

    def test_net_days_remaining_correct(self):
        result = assess_stockout_risk(delay_days=3.5, buffer_days=10.0, safety_stock_days=3)
        assert abs(result["net_days_remaining"] - 6.5) < 0.1
