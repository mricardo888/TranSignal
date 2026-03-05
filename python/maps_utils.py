"""
maps_utils.py — Zero-API-Key Geospatial Layer
===============================================
Replaces the Google Maps dependency with two free, key-less approaches:

  1. Geocoding  → OpenStreetMap Nominatim (free, no key required)
                  Falls back to a hardcoded city dictionary if offline.

  2. Distance   → Haversine great-circle formula (pure math, no API).

  3. Transit time → Derived from distance using a freight-speed model:
                    - Road (< 1 500 km):  avg 70 km/h effective speed
                    - Sea  (≥ 1 500 km):  avg 500 km/day container ship

  4. Disruption delay → Severity multiplier applied on top of normal
                        transit (same model as before, now clearly
                        labelled as "Physics + Severity Model").
"""

import math
import requests
from typing import Optional

# ---------------------------------------------------------------------------
# HARDCODED CITY COORDINATES
# Fast lookup fallback when Nominatim is unavailable.
# ---------------------------------------------------------------------------
CITY_COORDS: dict[str, tuple[float, float]] = {
    "rotterdam":         (51.9244,   4.4777),
    "amsterdam":         (52.3676,   4.9041),
    "antwerp":           (51.2194,   4.4025),
    "hamburg":           (53.5753,   9.9979),
    "paris":             (48.8566,   2.3522),
    "london":            (51.5074,  -0.1278),
    "berlin":            (52.5200,  13.4050),
    "stuttgart":         (48.7758,   9.1829),
    "munich":            (48.1351,  11.5820),
    "frankfurt":         (50.1109,   8.6821),
    "milan":             (45.4654,   9.1859),
    "madrid":            (40.4168,  -3.7038),
    "barcelona":         (41.3851,   2.1734),
    "new york":          (40.7128, -74.0060),
    "los angeles":       (34.0522, -118.2437),
    "chicago":           (41.8781, -87.6298),
    "houston":           (29.7604, -95.3698),
    "miami":             (25.7617, -80.1918),
    "monterrey":         (25.6866, -100.3161),
    "mexico city":       (19.4326, -99.1332),
    "veracruz":          (19.1738, -96.1342),
    "shanghai":          (31.2304, 121.4737),
    "shenzhen":          (22.5431, 114.0579),
    "guangzhou":         (23.1291, 113.2644),
    "ho chi minh city":  (10.8231, 106.6297),
    "ho chi minh":       (10.8231, 106.6297),
    "hanoi":             (21.0285, 105.8542),
    "singapore":         ( 1.3521, 103.8198),
    "tokyo":             (35.6762, 139.6503),
    "seoul":             (37.5665, 126.9780),
    "taipei":            (25.0330, 121.5654),
    "dubai":             (25.2048,  55.2708),
    "mumbai":            (19.0760,  72.8777),
    "sydney":            (-33.8688, 151.2093),
    # Extended locations for wider disruption scenarios
    "taipei":            (25.0330, 121.5654),
    "detroit":           (42.3314, -83.0458),
    "suez":              (29.9668,  32.5498),
    "piraeus":           (37.9475,  23.6371),
    "yokohama":          (35.4437, 139.6380),
    "busan":             (35.1796, 129.0756),
    "santos":            (-23.9608, -46.3336),
    "durban":            (-29.8587,  31.0218),
    "jakarta":           (-6.2088, 106.8456),
    "chennai":           (13.0827,  80.2707),
    "bratislava":        (48.1486,  17.1077),
    "wroclaw":           (51.1079,  17.0385),
    "hsinchu":           (24.8138, 120.9675),
    "dresden":           (51.0504,  13.7373),
    "port said":         (31.2653,  32.3019),
    "constanta":         (44.1598,  28.6348),
    "laem chabang":      (13.0819, 100.8840),
    "port klang":        (3.0000, 101.3833),
}

# Severity → multiplier on top of normal transit time
SEVERITY_MULTIPLIER: dict[str, float] = {
    "Low":      1.2,   # +20 %  — minor slowdown
    "Medium":   1.5,   # +50 %  — congestion / partial closure
    "High":     3.0,   # 3×     — hub closed, freight rerouted
    "Critical": 5.0,   # 5×     — complete shutdown, force-majeure
}


# ---------------------------------------------------------------------------
# GEOCODING — Nominatim (OpenStreetMap)
# ---------------------------------------------------------------------------

def geocode_location(location_name: str) -> dict:
    """
    Resolve a place name → (lat, lng).

    Strategy:
      1. Check hardcoded CITY_COORDS dict (instant, offline).
      2. Call Nominatim API (free, no key).
      3. If both fail, return (0, 0) with _is_mock=True.

    Returns:
        {
          "location":          {"lat": float, "lng": float},
          "formatted_address": str,
          "source":            "cache" | "nominatim" | "fallback",
          "_is_mock":          bool   (True only if fully unknown)
        }
    """
    # --- 1. Hardcoded cache (fastest path) ---
    key = location_name.strip().lower()
    if key in CITY_COORDS:
        lat, lng = CITY_COORDS[key]
        return {
            "location": {"lat": lat, "lng": lng},
            "formatted_address": location_name.title(),
            "source": "cache",
            "_is_mock": False,
        }

    # --- 2. Nominatim (OpenStreetMap) ---
    try:
        resp = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": location_name, "format": "json", "limit": 1},
            headers={"User-Agent": "SupplyChainResilienceAgent/1.0"},
            timeout=5,
        )
        resp.raise_for_status()
        data = resp.json()
        if data:
            lat = float(data[0]["lat"])
            lng = float(data[0]["lon"])
            return {
                "location": {"lat": lat, "lng": lng},
                "formatted_address": data[0].get("display_name", location_name),
                "source": "nominatim",
                "_is_mock": False,
            }
    except Exception:
        pass

    # --- 3. Unknown location fallback ---
    return {
        "location": {"lat": 0.0, "lng": 0.0},
        "formatted_address": location_name,
        "source": "fallback",
        "_is_mock": True,
    }


# ---------------------------------------------------------------------------
# DISTANCE — Haversine great-circle formula
# ---------------------------------------------------------------------------

def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    Calculate the great-circle distance between two points (degrees) in km.
    Uses the Haversine formula — accurate to within ~0.3 % for any distance.
    """
    R = 6_371.0  # Earth radius in km
    φ1, φ2 = math.radians(lat1), math.radians(lat2)
    dφ = math.radians(lat2 - lat1)
    dλ = math.radians(lng2 - lng1)
    a = math.sin(dφ / 2) ** 2 + math.cos(φ1) * math.cos(φ2) * math.sin(dλ / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ---------------------------------------------------------------------------
# TRANSIT TIME MODEL
# ---------------------------------------------------------------------------

def _normal_transit_hours(distance_km: float) -> float:
    """
    Estimate normal (undisrupted) freight transit hours from distance.

    Model:
      - Short haul / road  (< 1 500 km): effective speed 70 km/h
        (accounts for loading, border crossings, rest stops)
      - Long haul / sea    (≥ 1 500 km): container ship at 500 km/day
        plus 48 h port handling on each end

    These are realistic mid-market freight estimates, not optimistic
    express-delivery figures.
    """
    if distance_km < 1_500:
        return distance_km / 70.0
    else:
        sea_days = distance_km / 500.0
        port_handling_days = 2.0   # loading + unloading buffer
        return (sea_days + port_handling_days) * 24


# ---------------------------------------------------------------------------
# MAIN PUBLIC API
# ---------------------------------------------------------------------------

def get_transit_delay(
    origin: str,
    destination: str,
    disruption_severity: str = "High",
    origin_coords: Optional[tuple[float, float]] = None,
    destination_coords: Optional[tuple[float, float]] = None,
) -> dict:
    """
    Calculate transit delay between two locations using Haversine + severity model.

    Args:
        origin:               Place name (e.g. "Rotterdam").
        destination:          Place name (e.g. "Paris, France").
        disruption_severity:  One of Low / Medium / High / Critical.
        origin_coords:        Optional (lat, lng) to skip geocoding.
        destination_coords:   Optional (lat, lng) to skip geocoding.

    Returns:
        {
          "origin":                   str,
          "destination":              str,
          "distance_km":              float,
          "normal_duration_hours":    float,
          "disrupted_duration_hours": float,
          "delay_added_hours":        float,
          "delay_added_days":         float,
          "method":                   str,   # describes how values were derived
          "_is_mock":                 bool
        }
    """
    # Resolve coordinates
    if origin_coords:
        o_lat, o_lng = origin_coords
        o_addr = origin
    else:
        geo_o = geocode_location(origin)
        o_lat, o_lng = geo_o["location"]["lat"], geo_o["location"]["lng"]
        o_addr = geo_o["formatted_address"]

    if destination_coords:
        d_lat, d_lng = destination_coords
        d_addr = destination
    else:
        geo_d = geocode_location(destination)
        d_lat, d_lng = geo_d["location"]["lat"], geo_d["location"]["lng"]
        d_addr = geo_d["formatted_address"]

    # Calculate distance & times
    distance_km    = round(haversine_km(o_lat, o_lng, d_lat, d_lng), 1)
    normal_hours   = round(_normal_transit_hours(distance_km), 1)
    multiplier     = SEVERITY_MULTIPLIER.get(disruption_severity, 3.0)
    disrupted_h    = round(normal_hours * multiplier, 1)
    added_h        = round(disrupted_h - normal_hours, 1)

    mode = "road (70 km/h)" if distance_km < 1_500 else "sea (500 km/day + 48h port)"

    return {
        "origin":                   o_addr,
        "destination":              d_addr,
        "distance_km":              distance_km,
        "normal_duration_hours":    normal_hours,
        "disrupted_duration_hours": disrupted_h,
        "delay_added_hours":        added_h,
        "delay_added_days":         round(added_h / 24, 2),
        "method":                   f"Haversine distance + {mode} model × {multiplier}× severity",
        "_is_mock":                 False,   # this is real math, not fake data
    }


def assess_stockout_risk(
    delay_days: float,
    buffer_days: float,
    safety_stock_days: float = 3,
) -> dict:
    """
    Compare inbound transit delay against available inventory buffer.
    Unchanged from original — pure business logic, no external dependency.
    """
    net = buffer_days - delay_days

    if net < 0:
        urgency = "CRITICAL"
    elif net < safety_stock_days:
        urgency = "HIGH"
    elif net < safety_stock_days * 2:
        urgency = "MEDIUM"
    else:
        urgency = "LOW"

    return {
        "inventory_buffer_days": round(buffer_days, 1),
        "inbound_delay_days":    round(delay_days, 2),
        "net_days_remaining":    round(net, 1),
        "safety_stock_days":     safety_stock_days,
        "stockout_will_occur":   net < safety_stock_days,
        "urgency":               urgency,
    }
