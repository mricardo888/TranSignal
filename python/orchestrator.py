"""
orchestrator.py — Backend Orchestration Layer
==============================================
Handles the main pipeline logic separated from the Streamlit UI.
"""

import os
import time
import random
from datetime import datetime
import requests
import xml.etree.ElementTree as ET
from urllib.parse import quote as _urlquote

from erp_data import ERP_PROFILES
from maps_utils import geocode_location, get_transit_delay, assess_stockout_risk
from agent import run_agent

_DISRUPTION_KEYWORDS: dict[str, list[str]] = {
    "Port Strike":              ["port strike", "dock worker", "longshoreman strike", "port closure"],
    "Port Congestion":          ["port congestion", "shipping backlog", "vessel delay", "port queue"],
    "Factory Fire":             ["factory fire", "plant explosion", "industrial fire", "facility blaze"],
    "Customs Delay":            ["customs delay", "border clearance", "import hold", "customs backlog"],
    "Extreme Weather":          ["typhoon", "hurricane", "flood", "storm disruption", "extreme weather"],
    "Semiconductor Shortage":   ["chip shortage", "semiconductor shortage", "wafer supply", "fab capacity"],
    "Supplier Insolvency":      ["supplier bankruptcy", "company insolvency", "liquidation", "receivership"],
    "Geopolitical Sanctions":   ["trade sanctions", "export ban", "tariff escalation", "geopolitical tension"],
    "Raw Material Price Spike": ["raw material price", "commodity surge", "steel price", "copper price spike"],
    "Regulatory Change":        ["import regulation", "trade policy change", "customs regulation", "compliance mandate"],
}

def _classify_article(title: str) -> str:
    """Return the best-matching disruption type or 'General' if none match."""
    title_lower = title.lower()
    for dtype, keywords in _DISRUPTION_KEYWORDS.items():
        if any(kw in title_lower for kw in keywords):
            return dtype
    return "General"


def fetch_supply_chain_news(company_key: str, max_articles: int = 10) -> list[dict]:
    """
    Fetch Google News RSS articles relevant to the active ERP company's
    supply chain exposure.
    """
    erp = ERP_PROFILES[company_key]
    # Collect key locations from the profile
    locations: list[str] = []
    for sup in erp["suppliers"].values():
        locations.append(sup["city"])
        hub = sup.get("transit_hub", "")
        if "Port of" in hub:
            locations.append(hub.replace("Port of", "").strip().split(" ")[0])
    locations.append(erp["warehouse"]["city"])

    # Deduplicate, keep top 5 cities
    seen: set[str] = set()
    unique_locs: list[str] = []
    for loc in locations:
        if loc and loc not in seen:
            seen.add(loc)
            unique_locs.append(loc)
        if len(unique_locs) >= 5:
            break

    loc_query = " OR ".join(f'"{loc}"' for loc in unique_locs)
    query = f'({loc_query}) (supply chain OR logistics OR shipping OR disruption OR port OR semiconductor)'
    url = f"https://news.google.com/rss/search?q={_urlquote(query)}&hl=en-US&gl=US&ceid=US:en"

    articles: list[dict] = []
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}, timeout=8)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        channel = root.find("channel")
        if channel is None:
            return []
        for item in channel.findall("item")[:max_articles]:
            title    = item.findtext("title", "").strip()
            link     = item.findtext("link", "").strip()
            pub_date = item.findtext("pubDate", "").strip()
            source   = item.findtext("source", "").strip()
            if not title:
                continue
            articles.append({
                "title":    title,
                "link":     link,
                "pub_date": pub_date[:16] if pub_date else "",   # trim seconds
                "source":   source,
                "dtype":    _classify_article(title),
            })
    except Exception:
        pass

    return articles


def run_full_pipeline_step1_perception(event: dict, erp: dict, add_log_cb):
    warehouse = erp["warehouse"]
    
    src_tag = " [AUTO-DETECTED 🛰]" if event.get("source") == "AUTO_DETECTED" else ""
    add_log_cb(f"[PERCEPTION]{src_tag} Geocoding disruption: {event['location']}…", "info")

    geo = geocode_location(event["location"])
    geo_note = " (cache)" if geo.get("source") == "cache" else \
               " (Nominatim)" if geo.get("source") == "nominatim" else " (fallback)"
    
    add_log_cb(
        f"[PERCEPTION] Resolved{geo_note}: {geo['formatted_address']} "
        f"({geo['location']['lat']:.3f}, {geo['location']['lng']:.3f})",
        "info",
    )

    transit = get_transit_delay(
        origin=event["location"],
        destination=f"{warehouse['city']}, {warehouse['country']}",
        disruption_severity=event["severity"],
    )
    add_log_cb(
        f"[PERCEPTION] Transit model: {transit['distance_km']} km | "
        f"normal {transit['normal_duration_hours']}h → disrupted {transit['disrupted_duration_hours']}h "
        f"(+{transit['delay_added_days']}d)",
        "warning",
    )
    return transit, geo

def run_full_pipeline_step2_risk(delay_added_days: float, inv: dict, buf: float, add_log_cb):
    risk = assess_stockout_risk(delay_added_days, buf, inv["safety_stock_days"])
    
    level_map = {"LOW": "info", "MEDIUM": "warning", "HIGH": "critical", "CRITICAL": "critical"}
    add_log_cb(
        f"[RISK] Buffer {risk['inventory_buffer_days']}d − delay {risk['inbound_delay_days']}d "
        f"= {risk['net_days_remaining']}d remaining | Urgency: {risk['urgency']}",
        level_map.get(risk["urgency"], "warning"),
    )
    if risk["stockout_will_occur"]:
        add_log_cb(
            f"[RISK] ⚠ STOCKOUT WARNING — net buffer below {risk['safety_stock_days']}d safety stock.",
            "critical",
        )
    return risk

def run_full_pipeline_step3_reasoning(event: dict, transit: dict, risk: dict, erp: dict, add_log_cb):
    add_log_cb("[REASONING] Injecting memory context + ERP profile into Gemini prompt…", "info")
    
    result = run_agent(
        disruption_event=event,
        transit_data=transit,
        risk_assessment=risk,
        erp_data=erp,
    )
    
    src_note = " (mock)" if result.get("_is_mock") else " (live Gemini 2.5 Flash)"
    if result.get("_api_error"):
        add_log_cb(f"[REASONING] ⚠ API error — showing mock fallback: {result['_api_error']}", "critical")
    else:
        add_log_cb(f"[REASONING] Response received{src_note}.", "success")

    strategy = result.get("chosen_strategy", {})
    add_log_cb(
        f"[DECISION] {strategy.get('name','?')} — premium: ${strategy.get('cost_premium_usd',0):,}",
        "success",
    )

    hitl = result.get("hitl_flag", {})
    if hitl.get("requires_human_approval"):
        add_log_cb(
            f"[HITL] 🚦 Escalating to {hitl.get('escalate_to')} — deadline {hitl.get('deadline_hours')}h.",
            "warning",
        )
    else:
        add_log_cb("[ACTION] ✅ Autonomous action authorised — within threshold.", "success")
        
    return result
