import os
import json
from erp_data import ERP_PROFILES
from orchestrator import run_full_pipeline_step1_perception, run_full_pipeline_step2_risk, run_full_pipeline_step3_reasoning

def add_log(msg: str, level: str = "info") -> None:
    print(f"[{level.upper()}] {msg}")

def main():
    erp = ERP_PROFILES["🚗 TexMex Components — Mexico (Multi-source)"]
    
    event = {
        "event":     "Factory Fire",
        "location":  "Monterrey",
        "severity":  "Critical",
        "timestamp": "2026-03-05T17:50:00",
        "source":    "MANUAL",
    }
    
    print("--- STEP 1 ---")
    transit, geo = run_full_pipeline_step1_perception(event, erp, add_log)
    
    print("\n--- STEP 2 ---")
    buf = 10.0 # get_inventory_buffer_days
    risk = run_full_pipeline_step2_risk(transit["delay_added_days"], erp["inventory"], buf, add_log)
    
    print("\n--- STEP 3 ---")
    result = run_full_pipeline_step3_reasoning(event, transit, risk, erp, add_log)
    
    print("\n--- RESULT ---")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
