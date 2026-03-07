# TranSignal — Autonomous Supply Chain Resilience Agent

TranSignal is an Autonomous Supply Chain Resilience Agent designed to help mid-market manufacturers proactively predict, mitigate, and respond to global supply chain disruptions. 

Developed in response to the Hack the Future (HTF) case challenge, TranSignal leverages Google's Gemini 2.5 Flash GenAI to function as an intelligent operations co-pilot. It moves beyond traditional static dashboards by actively perceiving disruption signals, reasoning through complex logistics scenarios, simulating financial trade-offs, and orchestrating mitigation strategies before SLA breaches or production line stockouts occur.

---

## Architecture & Technical Implementation

TranSignal is engineered with a production-ready, decoupled agentic architecture aligned directly with the HTF technical criteria.

*   **Google GenAI Ecosystem:** Utilizes Gemini 2.5 Flash as the core reasoning engine, parsing unstructured disruption data and evaluating multi-dimensional supply chain trade-offs.
*   **Decoupled Backend API (`python/api.py`):** A robust FastAPI service handling AI endpoints, deterministic math operations, and integrations. This allows the AI logic to operate headlessly.
*   **Autonomous Daemon (`python/daemon.py`):** The engine driving "Proactive Autonomy." A lightweight Python worker that continuously polls for disruption signals and executes the full reasoning pipeline without requiring human intervention.
*   **Operations Control Tower (`python/app.py`):** A Streamlit-based frontend dashboard featuring geospatial PyDeck mapping, interactive agent reasoning traces, and the Gemini-powered Strategic Co-Pilot.
*   **Memory Integration (`python/memory.py`):** A persistent storage layer (Google Cloud Firestore or local JSON fallback) that logs disruption resolutions. This enables a feedback loop where the agent learns from past mitigation successes and failures.

---

## Core Capabilities (Aligned to HTF Requirements)

### 1. Perception Layer & Live Monitoring
The system ingests real-time supply chain disruption data. The background daemon auto-detects events (e.g., port strikes, factory fires) via simulated RSS news ingestion, classifying supply risk and immediately triggering the agent evaluation pipeline.

### 2. Risk Intelligence Engine & Financial Impact
The system calculates rigorous, quantifiable risk exposure. 
*   **Revenue-at-Risk Estimation:** Evaluates exact financial exposure based on specific Customer Service-Level Agreements (SLAs) and daily production value.
*   **Operational Impact Modeling:** Uses deterministic calculations to assess inventory buffer days and predict stockout probabilities.

### 3. Planning & Decision Engine (Multi-Step Reasoning)
When a disruption is detected, TranSignal simulates trade-offs. The Gemini-powered reasoning trace explicitly evaluates the manufacturer's unique profile:
*   **Hyper-Personalization:** Mitigation strategies adapt drastically based on the specific company's Risk Appetite, Supplier Concentration, and Buffer Policies.
*   **Trade-Off Simulation:** The agent balances the cost premium of expedited shipping (e.g., air freight from a secondary supplier) against the financial penalty of missing SLA deliveries.

### 4. Autonomous Action Layer
TranSignal bridges the gap between recommendation and execution. Once a strategy is formulated, the agent outputs tangible actions:
*   **ERP Payload Generation:** Outputs structured JSON payloads ready for transmission to enterprise resource planning systems (e.g., PO adjustments, warehouse rerouting).
*   **Supplier Communication:** Auto-generates fully drafted supplier negotiation and procurement emails.

### 5. Explainability & Responsible AI (Risk Controls)
To ensure trust and transparency, the agent is bounded by strict constraints:
*   **Human-In-The-Loop (HITL) Enforcement:** The system enforces a defined `autonomous_action_limit_usd`. Strategies exceeding an organization's specific cost threshold or operating below a 70% confidence score are automatically halted and escalated to management for absolute oversight.
*   **Reasoning Trace UI:** The frontend exposes exactly *why* the AI made its decision, matching requirements for transparent reasoning.

---

## Getting Started

### Prerequisites

*   Python 3.10+
*   Google Gemini API Key
*   (Optional) Firebase Admin Credentials for Cloud Memory

### 1. Installation

Clone the repository and install the required dependencies:

```bash
git clone <your-repo-url>
cd TranSignal/python

python -m venv .venv

# Mac/Linux
source .venv/bin/activate
# Windows
.venv\Scripts\activate

pip install -r requirements.txt
```

### 2. Configuration

Create a `.env` file in the `python/` directory and configure your keys:

```env
GEMINI_API_KEY="your_api_key_here"
BACKEND_URL="http://127.0.0.1:8000"
# FIREBASE_CREDENTIALS="..." # Optional
```

### 3. Running the Platform

We provide automated scripts to launch both the decoupled Backend API (with the background daemon) and the Streamlit Frontend simultaneously.

**Mac / Linux:**
Open a terminal in the root `TranSignal/` directory and run:
```bash
./run.sh
```

**Windows:**
Double-click the `run.bat` script in the root directory, or execute it from the Command Prompt:
```cmd
run.bat
```

The TranSignal Operations Control Tower will automatically launch in your browser at `http://localhost:8501`.

---

## Golden Path Demo Guide
*For evaluators and judges reviewing this project, we recommend the following sequence:*

1.  **Dashboard Initialization:** Open the UI. Set the Company Profile to **"AcmeMfg GmbH"** (A highly concentrated manufacturer in Germany with strict SLA requirements).
2.  **Disruption Simulation:** On the sidebar, locate the "Disruption Simulator". Select an event type (e.g., "Port Strike" in "Rotterdam") and click **Simulate**.
3.  **Real-Time Perception & Mapping:** Observe the pipeline execution. A Red Arc (blocked inbound transit) and a Green Arc (AI-calculated rerouted transit) will render on the global map.
4.  **Financial Value Generation:** Review the "Impact Analysis" charts comparing the cost of the AI Intervention directly against the financial loss of "Doing Nothing".
5.  **Reasoning Trace Transparency:** Open the **"🧠 Reasoning Trace"** tab to independently audit the agent's 5-step logic and the deterministic Bias & Constraint validation table.
6.  **Human-In-The-Loop (HITL):** Open the **"⚡ Strategy & Action"** tab. Note whether the action was executed autonomously or if it was halted for Human Approval because it exceeded AcmeMfg's specific risk thresholds. Review the generated ERP JSON payload. 
7.  **Hyper-Personalization Test:** Switch the active company to **"TexMex Components"** (Mexico-based, high risk appetite). Simulate another disruption to observe a completely different, fully autonomous mitigation strategy tailored to their specific operational constraints.
