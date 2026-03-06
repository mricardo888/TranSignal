"""
erp_data.py — Mock ERP System Data
===================================
Two distinct company profiles demonstrating hyper-personalisation:

  1. AcmeMfg GmbH (Germany)
     - Semiconductor-dependent, single-source from Rotterdam corridor
     - Conservative risk appetite, strict SLA with EuroAuto Industries
     - Disruption → agent recommends SPLIT_ORDER (cautious)

  2. TexMex Components S.A. (Mexico)
     - Automotive wire harness, already multi-sourced across 3 continents
     - Medium risk appetite, high burn rate, large inventory buffer
     - Disruption → agent recommends ACTIVATE_SECONDARY (decisive)

The contrast between the two outputs is the live proof of hyper-personalisation.
"""

# ---------------------------------------------------------------------------
# PROFILE 1 — AcmeMfg GmbH (Germany) — Single-source, conservative
# ---------------------------------------------------------------------------
_ACME = {
    "company": "AcmeMfg GmbH",
    "product": "Industrial Servo Motor (SKU: ISM-4400)",
    "profile_type": "semiconductor_dependent",
    "risk_appetite": "low",
    "concentration_risk": "high",  # 90% inbound via Rotterdam corridor

    "inventory": {
        "on_hand_units": 500,
        "burn_rate_per_day": 50,
        "safety_stock_days": 3,
        "reorder_point_units": 200,
    },

    "suppliers": {
        "primary": {
            "id": "SUP-A",
            "name": "Precision Parts GmbH",
            "city": "Stuttgart",
            "country": "Germany",
            "lat": 48.7758,
            "lon": 9.1829,
            "normal_lead_time_days": 7,
            "unit_cost_usd": 42.50,
            "active_po_units": 1000,
            "transit_hub": "Port of Rotterdam",
            "contact_email": "orders@precisionparts.de",
            "role": "Primary",
            "color": [56, 139, 253, 220],
            "reliability_score": 0.95,
        },
        "secondary": {
            "id": "SUP-B",
            "name": "Motores Avanzados S.A.",
            "city": "Monterrey",
            "country": "Mexico",
            "lat": 25.6866,
            "lon": -100.3161,
            "normal_lead_time_days": 14,
            "unit_cost_usd": 38.00,
            "active_po_units": 0,
            "transit_hub": "Port of Veracruz",
            "contact_email": "procurement@motoresavanzados.mx",
            "role": "Secondary",
            "color": [63, 185, 80, 220],
            "reliability_score": 0.82,
        },
        "tertiary": {
            "id": "SUP-C",
            "name": "VietPrecision Co. Ltd",
            "city": "Ho Chi Minh City",
            "country": "Vietnam",
            "lat": 10.8231,
            "lon": 106.6297,
            "normal_lead_time_days": 21,
            "unit_cost_usd": 31.00,
            "active_po_units": 0,
            "transit_hub": "Port of Ho Chi Minh City",
            "contact_email": "sales@vietprecision.vn",
            "role": "Tertiary",
            "color": [210, 153, 34, 220],
            "reliability_score": 0.75,
        },
    },

    "warehouse": {
        "name": "Paris Distribution Hub",
        "city": "Paris",
        "country": "France",
        "lat": 48.8566,
        "lon": 2.3522,
        "color": [255, 255, 255, 220],
    },

    "sla": {
        "max_acceptable_delay_days": 5,
        "daily_production_value_usd": 85_000,
        "key_customer": "EuroAuto Industries",
        "autonomous_action_limit_usd": 20_000,
        "revenue_per_day": 85_000,
    },

    # Default map view: centred on Europe/Asia
    "map_view": {"latitude": 30, "longitude": 20, "zoom": 1.4},

    # Scripted auto-detection alerts for monitoring mode
    "auto_alerts": [
        {"event": "Port Strike",             "location": "Rotterdam",  "severity": "High"},
        {"event": "Extreme Weather",         "location": "Hamburg",    "severity": "Critical"},
        {"event": "Customs Delay",           "location": "Antwerp",    "severity": "Medium"},
        {"event": "Semiconductor Shortage",   "location": "Hsinchu",   "severity": "Critical"},
        {"event": "Supplier Insolvency",      "location": "Dresden",   "severity": "High"},
        {"event": "Geopolitical Sanctions",   "location": "Shanghai",  "severity": "Critical"},
        {"event": "Port Congestion",          "location": "Piraeus",   "severity": "Medium"},
        {"event": "Raw Material Price Spike", "location": "Durban",    "severity": "High"},
        {"event": "Regulatory Change",        "location": "Berlin",    "severity": "Medium"},
    ],
}


# ---------------------------------------------------------------------------
# PROFILE 2 — TexMex Components S.A. (Mexico) — Multi-sourced, decisive
# ---------------------------------------------------------------------------
_TEXMEX = {
    "company": "TexMex Components S.A.",
    "product": "Automotive Wire Harness (SKU: AWH-2200)",
    "profile_type": "multi_sourced_automotive",
    "risk_appetite": "medium",
    "concentration_risk": "low",   # 3 active suppliers across 3 continents

    "inventory": {
        "on_hand_units": 3_000,
        "burn_rate_per_day": 300,   # high-volume automotive assembly line
        "safety_stock_days": 5,
        "reorder_point_units": 1_500,
    },

    "suppliers": {
        "primary": {
            "id": "SUP-X1",
            "name": "Grupo Electrico Monterrey",
            "city": "Monterrey",
            "country": "Mexico",
            "lat": 25.6866,
            "lon": -100.3161,
            "normal_lead_time_days": 3,
            "unit_cost_usd": 12.00,
            "active_po_units": 5_000,
            "transit_hub": "Monterrey Industrial Park (road)",
            "contact_email": "ops@grupoelectrico.mx",
            "role": "Primary",
            "color": [56, 139, 253, 220],
            "reliability_score": 0.88,
        },
        "secondary": {
            "id": "SUP-X2",
            "name": "AutoWire USA Corp.",
            "city": "Houston",
            "country": "USA",
            "lat": 29.7604,
            "lon": -95.3698,
            "normal_lead_time_days": 5,
            "unit_cost_usd": 14.50,
            "active_po_units": 0,
            "transit_hub": "Port of Houston",
            "contact_email": "orders@autowireusa.com",
            "role": "Secondary",
            "color": [63, 185, 80, 220],
            "reliability_score": 0.99,
        },
        "tertiary": {
            "id": "SUP-X3",
            "name": "Guangzhou HarnessWorks Ltd",
            "city": "Guangzhou",
            "country": "China",
            "lat": 23.1291,
            "lon": 113.2644,
            "normal_lead_time_days": 18,
            "unit_cost_usd": 9.00,
            "active_po_units": 0,
            "transit_hub": "Port of Guangzhou",
            "contact_email": "export@gzharnessworks.cn",
            "role": "Tertiary",
            "color": [210, 153, 34, 220],
            "reliability_score": 0.85,
        },
    },

    "warehouse": {
        "name": "San Antonio Assembly Hub",
        "city": "San Antonio",
        "country": "USA",
        "lat": 29.4241,
        "lon": -98.4936,
        "color": [255, 255, 255, 220],
    },

    "sla": {
        "max_acceptable_delay_days": 2,   # automotive JIT — very tight
        "daily_production_value_usd": 120_000,
        "key_customer": "Ford Motor Company — Hermosillo Plant",
        "autonomous_action_limit_usd": 50_000,  # higher autonomy threshold
        "revenue_per_day": 120_000,
    },

    # Default map view: centred on Americas
    "map_view": {"latitude": 25, "longitude": -90, "zoom": 2.5},

    # Scripted auto-detection alerts for monitoring mode
    "auto_alerts": [
        {"event": "Factory Fire",             "location": "Monterrey",  "severity": "Critical"},
        {"event": "Customs Delay",            "location": "Houston",    "severity": "Medium"},
        {"event": "Extreme Weather",          "location": "Guangzhou",  "severity": "High"},
        {"event": "Semiconductor Shortage",   "location": "Taipei",     "severity": "High"},
        {"event": "Supplier Insolvency",      "location": "Detroit",    "severity": "High"},
        {"event": "Geopolitical Sanctions",   "location": "Shenzhen",   "severity": "Critical"},
        {"event": "Port Congestion",          "location": "Santos",     "severity": "Medium"},
        {"event": "Raw Material Price Spike", "location": "Jakarta",    "severity": "High"},
        {"event": "Regulatory Change",        "location": "Mexico City","severity": "Medium"},
    ],
}


# ---------------------------------------------------------------------------
# PROFILES REGISTRY
# ---------------------------------------------------------------------------
ERP_PROFILES: dict[str, dict] = {
    "🏭 AcmeMfg GmbH — Germany (Single-source)":   _ACME,
    "🚗 TexMex Components — Mexico (Multi-source)": _TEXMEX,
}

# Default profile (backward compatibility with existing imports)
ERP_DATA = _ACME


# ---------------------------------------------------------------------------
# HELPER FUNCTIONS (all accept an optional erp_data override)
# ---------------------------------------------------------------------------

def get_inventory_buffer_days(erp_data: dict | None = None) -> float:
    """How many days of production the current on-hand stock covers."""
    d = erp_data or ERP_DATA
    inv = d["inventory"]
    return inv["on_hand_units"] / inv["burn_rate_per_day"]


def get_suppliers_as_dataframe_rows(erp_data: dict | None = None) -> list[dict]:
    """Return supplier + warehouse records as a flat list for pydeck."""
    d = erp_data or ERP_DATA
    rows = []
    for sup in d["suppliers"].values():
        rows.append({
            "name": f"{sup['name']} ({sup['city']}, {sup['country']})",
            "role": sup["role"],
            "lat": sup["lat"],
            "lon": sup["lon"],
            "color": sup["color"],
        })
    wh = d["warehouse"]
    rows.append({
        "name": f"🏭 {wh['name']}",
        "role": "Warehouse",
        "lat": wh["lat"],
        "lon": wh["lon"],
        "color": wh["color"],
    })
    return rows
