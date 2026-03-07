# 🏭 TranSignal — Autonomous Supply Chain Resilience Agent

**An AI Operations Co-Pilot built for Mid-Market Manufacturers.**

Global supply chains are entering an era of structural volatility. When a port goes on strike or a factory catches fire, mid-market manufacturers without massive supply chain control towers lose millions in Service Level Agreement (SLA) penalties. 

**TranSignal** solves this by transforming supply chain management from reactive to *autonomous*. 

Powered by **Gemini 2.5 Flash**, TranSignal doesn't just alert humans to a problem on a dashboard. It is a true Autonomous Agent that actively perceives disruption signals, calculates exact "Revenue at Risk", simulates spatial and financial trade-offs, and executes optimal mitigation actions (like auto-drafting logistics emails and generating ERP system payloads).

---

## 🏆 Why this wins (Key Features)

* **💸 Immediate Financial ROI:** TranSignal calculates exactly how much revenue is at risk based on customer SLAs and daily production value. It proves mathematically that paying a $7,500 shipping premium is worth it to protect $120,000/day in SLA penalties.
* **🛰️ Proactive Autonomy:** Complete decoupled architecture. A background daemon continuously monitors global RSS nodes and internal inventory buffers, resolving disruptions before humans even open the dashboard.
* **🧠 Deterministic + LLM Architecture:** We pair Gemini's reasoning engine with deterministic math (Haversine geospatial distance, inventory burn rate formulas) to prevent LLM hallucination on critical operations data.
* **🚦 Human-in-the-Loop Safeguards:** Dynamic thresholds ensure the AI operates autonomously on routine disruptions but halts and requires human approval for high-risk or high-cost strategies.
* **🗂️ Memory & Learning System:** The agent maintains a persistent Firebase vector memory. Outcomes of past mitigations (e.g. "Stockout Occurred") are fed back into Gemini's next reasoning cycle, ensuring the AI gets smarter over time.

---

## 🚀 Quick Start (For Judges)

We have provided a unified script to run both the decoupled Backend API and the Streamlit Control Tower simultaneously.

### Prerequisites
1. Python 3.10+
2. Set your API Key: Create a `.env` file in the `python/` directory and add:
   ```env
   GEMINI_API_KEY="your_actual_key_here"
   # Optional: FIREBASE_CREDENTIALS="..." 
   ```

### Running the App
1. **Mac / Linux:**
   Open a terminal in the root directory and run:
   ```bash
   ./run.sh
   ```
2. **Windows:**
   Double-click the script or run from Command Prompt:
   ```cmd
   run.bat
   ```

The Streamlit Operations Control Tower will automatically open in your browser at `http://localhost:8501`.

---

## 🏗️ Architecture Stack

This project is built using a production-ready, decoupled AI operational stack:

* **Google GenAI (Gemini 2.5 Flash):** Core reasoning engine, multi-step trace generation, and conversational co-pilot interactions.
* **FastAPI Backend (`python/api.py`):** Serves the AI logic and memory layer as an independent API, allowing integration into actual enterprise software.
* **Python Headless Daemon (`python/daemon.py`):** The autonomous watcher that operates independently of the frontend, scraping RSS feeds and firing endpoints.
* **Streamlit Frontend (`python/app.py`):** The Operations Control Tower featuring dark-matter PyDeck mapping and interactive agent reasoning traces.
* **Google Cloud Firestore / Local JSON Memory:** Persistent learning layer that stores agent states and outcomes.

---

## 🧪 Golden Path Demo Script
*If you are judging this project, try the following sequence to experience the full AI capabilities:*

1. Open the UI. Set the Company Profile to **"AcmeMfg GmbH"** (A highly concentrated manufacturer in Germany).
2. Look at the **"Disruption Simulator"** on the sidebar. Choose "Port Strike" in "Rotterdam". Hit **Simulate**.
3. Watch the AI execute in real-time. Notice the **Red Arc** (blocked route) and **Green Arc** (AI reroute) appear on the map.
4. Open the **"🧠 Reasoning Trace"** tab to read Gemini's 5-step internal thought process.
5. View the **"⚡ Strategy & Action"** tab. Note that the $23k intervention triggered a **Human-in-the-Loop** block because it exceeded AcmeMfg's $20k threshold. 
6. Observe the **"📧 Draft Email"** tab and the auto-generated JSON ERP payload waiting for transmission.
7. Change the Company to **"TexMex Components"** (Mexico-based, high risk appetite). Simulate another disruption to observe a completely different, fully autonomous mitigation strategy!
