"""
daemon.py — Autonomous Background Agent Loop
=============================================
This headless worker continuously monitors external signals (RSS news),
orchestrates the agent's perception, reasoning, and actions, and logs 
decisions proactively without waiting for human input.
"""

import time
import uuid
import json
import logging
from datetime import datetime

from erp_data import ERP_PROFILES
from orchestrator import (
    fetch_supply_chain_news,
    run_full_pipeline_step1_perception,
    run_full_pipeline_step2_risk,
    run_full_pipeline_step3_reasoning,
)
from memory import save_event

# Minimal logging configuration for the daemon
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def add_log_cb(msg: str, level: str = "info") -> None:
    if level in ["critical", "error"]:
        logging.error(msg)
    elif level == "warning":
        logging.warning(msg)
    else:
        logging.info(msg)

# Track processed items to avoid re-triggering the same disruption
PROCESSED_LOG = set()

def monitor_loop(interval_seconds: int = 60, max_iterations: int = 0):
    """
    Infinite loop that checks news for all profiles and triggers the agent.
    If max_iterations is > 0, it stops after that many iterations (useful for testing).
    """
    logging.info(f"🚀 Starting Autonomous Supply Chain Agent Daemon... Poll interval: {interval_seconds}s")
    
    iteration = 0
    while True:
        iteration += 1
        logging.info("--- Starting Polling Cycle ---")
        
        for company_key, profile in ERP_PROFILES.items():
            logging.info(f"Fetching signals for: {company_key}")
            articles = fetch_supply_chain_news(company_key, max_articles=5)
            
            if not articles:
                logging.info(f"  No relevant new signals for {company_key}.")
                continue
                
            for article in articles:
                # Unique identifier for the article to prevent double-processing
                item_id = article.get("link", article.get("title"))
                if item_id in PROCESSED_LOG:
                    continue
                
                # Check if it's severe enough to care about (this acts as an initial filter)
                if article["dtype"] != "General":
                    logging.warning(f"🚨 ACTIVE THREAT DETECTED: {article['title']}")
                    logging.info(f"  Type: {article['dtype']} | Source: {article['source']}")
                    
                    # Convert the news article signal into a disruption event dictionary
                    # We make an educated guess about the location based on the query that fetched it.
                    # Or we extract cities from the title for a production system.
                    # For this daemon, we'll try to find an ERP location mentioned in the title.
                    detected_location = profile["warehouse"]["city"] # fallback
                    locations_to_check = [profile["warehouse"]["city"]] + [s["city"] for s in profile["suppliers"].values()]
                    for loc in locations_to_check:
                        if loc.lower() in article["title"].lower():
                            detected_location = loc
                            break
                            
                    event = {
                        "event": article["dtype"],
                        "location": detected_location,
                        "severity": "High", # Defaulting to High for external news
                        "timestamp": article.get("pub_date", datetime.now().strftime("%Y-%m-%dT%H:%M:%S")),
                        "source": "AUTO_DETECTED_RSS",
                        "title": article["title"],
                        "link": article["link"]
                    }
                    
                    logging.info(f"Executing Agent Pipeline for {company_key}...")
                    
                    try:
                        # 1: Perception
                        transit, geo = run_full_pipeline_step1_perception(event, profile, add_log_cb)
                        
                        # 2: Risk
                        risk = run_full_pipeline_step2_risk(transit["delay_added_days"], profile, add_log_cb)
                        
                        # 3: Reasoning & Strategy
                        result = run_full_pipeline_step3_reasoning(event, transit, risk, profile, add_log_cb)
                        strategy = result.get("chosen_strategy", {})
                        
                        # 4: Action/Escalation
                        hitl = result.get("hitl_flag", {})
                        if hitl.get("requires_human_approval"):
                            logging.warning(f"🛑 ACTION PAUSED: High-value override required. Escalating to {hitl.get('escalate_to')}")
                            # In production: send Slack/Email alert here
                        else:
                            logging.info(f"✅ AUTO-EXECUTING ALIGNMENT: {strategy.get('name')}")
                            # In production: trigger API calls (PO email) here
                            
                        # 5: Memory
                        rid = save_event(
                            company=profile["company"],
                            event=event,
                            risk=risk,
                            strategy=strategy,
                        )
                        logging.info(f"🧠 Logged to Memory Vector (ID: {rid})")
                        
                    except Exception as e:
                        logging.error(f"Pipeline failed for {company_key}: {e}")
                    
                    # Mark as processed
                    PROCESSED_LOG.add(item_id)
        
        if max_iterations > 0 and iteration >= max_iterations:
            logging.info("Max iterations reached. Stopping daemon.")
            break
            
        time.sleep(interval_seconds)

if __name__ == "__main__":
    # In a real environment, you run monitor_loop(60)
    # For testing, we just do 1 loop to see it work.
    monitor_loop(interval_seconds=60, max_iterations=0)
