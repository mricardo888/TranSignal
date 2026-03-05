"""
api.py — TranSignal Backend FastAPI Service
===========================================
This API wraps the orchestrator, agent, and memory functions
so the frontend can call them securely over HTTP.
It also starts the background autonomous daemon on boot.
"""

import os
import threading
from typing import Dict, Any, List
from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
import uvicorn

from orchestrator import (
    fetch_supply_chain_news,
    run_full_pipeline_step1_perception,
    run_full_pipeline_step2_risk,
    run_full_pipeline_step3_reasoning,
)
from memory import load_memory, save_event, clear_memory, get_stats, update_outcome
from daemon import monitor_loop

app = FastAPI(title="TranSignal AI Agent Backend")

# --- Background Daemon Startup ---
@app.on_event("startup")
def startup_event():
    print("🚀 Starting API Server & Background Daemon Thread...")
    # Run the autonomous monitoring loop as a daemon thread so it dies when the server dies
    monitor_thread = threading.Thread(
        target=monitor_loop, 
        kwargs={"interval_seconds": 60, "max_iterations": 0}, 
        daemon=True
    )
    monitor_thread.start()

# --- Schemas ---
class EventPayload(BaseModel):
    event: Dict[str, Any]
    profile: Dict[str, Any]

class RiskPayload(BaseModel):
    delay_added_days: float
    inventory: Dict[str, Any]
    buf_days: float

class ReasoningPayload(BaseModel):
    event: Dict[str, Any]
    transit: Dict[str, Any]
    risk: Dict[str, Any]
    profile: Dict[str, Any]

class MemorySavePayload(BaseModel):
    company: str
    event: Dict[str, Any]
    risk: Dict[str, Any]
    strategy: Dict[str, Any]

class OutcomePayload(BaseModel):
    outcome: str

# --- Endpoints ---
@app.get("/")
def health_check():
    return {"status": "ok", "service": "TransSignal AI API"}

@app.get("/news")
def get_news(company: str):
    """Fetch global supply chain news for a specific profile name."""
    try:
        articles = fetch_supply_chain_news(company)
        return {"articles": articles}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/pipeline/perception")
def perception_step(req: EventPayload):
    try:
        # A dummy callback since logging happens on the server now
        transit, geo = run_full_pipeline_step1_perception(req.event, req.profile, lambda msg, lvl="info": None)
        return {"transit": transit, "geo": geo}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/pipeline/risk")
def risk_step(req: RiskPayload):
    try:
        risk = run_full_pipeline_step2_risk(req.delay_added_days, req.inventory, req.buf_days, lambda msg, lvl="info": None)
        return {"risk": risk}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/pipeline/reasoning")
def reasoning_step(req: ReasoningPayload):
    try:
        result = run_full_pipeline_step3_reasoning(req.event, req.transit, req.risk, req.profile, lambda msg, lvl="info": None)
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Memory Endpoints ---
@app.get("/memory")
def get_memory():
    return {"records": load_memory(), "stats": get_stats()}

@app.post("/memory")
def create_memory(req: MemorySavePayload):
    rid = save_event(req.company, req.event, req.risk, req.strategy)
    return {"record_id": rid}

@app.put("/memory/{record_id}/outcome")
def set_memory_outcome(record_id: str, req: OutcomePayload):
    try:
        update_outcome(record_id, req.outcome)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/memory")
def wipe_memory():
    clear_memory()
    return {"status": "success"}

if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), reload=True)
