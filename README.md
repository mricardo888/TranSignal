# 🏭 TranSignal — AI Supply Chain Co-Pilot

TranSignal is an Autonomous Supply Chain Resilience Agent designed to help mid-market manufacturers predict, mitigate, and proactively respond to global supply chain disruptions. 

Powered by **Gemini 2.5 Flash**, TranSignal moves beyond traditional dashboards by actively reasoning through complex logistics scenarios, calculating financial impacts, and executing mitigation strategies (e.g., rerouting, split orders, emergency air freight) before a stockout occurs.

## 🚀 Key Features

* **🛰️ Perception & Auto-Detection**: A background daemon continuously monitors global RSS feeds and internal ERP signals to detect disruptions (e.g., Port Strikes, Factory Fires) without human intervention.
* **📦 Dynamic Risk Assessment**: Calculates precise "Revenue at Risk" based on Customer SLA penalties and real-time inventory burn rates.
* **🧠 Gemini Reasoning Engine**: Evaluates supplier trade-offs (Cost vs. Speed vs. Reliability) using a deterministic model combined with Gemini's reasoning trace to select the optimal strategy.
* **🔌 Autonomous Action Execution**: Generates structured JSON payloads for seamless ERP integration (e.g., PO Creation/Modification) and drafts supplier communication emails.
* **🚦 Human-in-the-Loop (HITL) Enforcement**: Automatically flags high-cost or high-risk decisions for human review based on configurable financial thresholds and company risk appetite.
* **🗂️ Memory & Reflection**: Learns from past mitigation outcomes. Successful strategies are reinforced, while failures (e.g., resulting in stockouts) guide the agent to pivot strategies in future disruptions.
* **💬 Interactive Co-Pilot Chat**: Allows supply chain managers to dynamically interrogate the AI's strategy, request adjustments, and collaboratively iterate on plans using a natural language interface.

## 🏗️ Architecture

TranSignal uses a decoupled, production-ready architecture:

* **Backend API (`python/api.py`)**: A `FastAPI` service that orchestrates the AI reasoning, geospatial transit analysis (Haversine + Nominatim), and persistent memory logging.
* **Frontend UI (`python/app.py`)**: A `Streamlit` app that serves as the Operations Control Tower, offering rich visualizations (PyDeck maps, interactive tabs) and the Chat Co-Pilot.
* **Background Daemon (`python/daemon.py`)**: A lightweight Python daemon that runs autonomously to monitor for disruptions and can trigger the API layer independently of the frontend.
* **Memory Layer (`python/memory.py`)**: Integrates with Google Cloud Firestore (or local JSON fallback) for persistent memory storage and learning.

## 🛠️ Getting Started

### Prerequisites

* Python 3.10+
* A Google Gemini API Key
* (Optional) Firebase Admin Credentials for Cloud Memory

### Installation

1. Clone the repository and navigate to the project directory:
   ```bash
   git clone <your-repo-url>
   cd TranSignal/python
   ```

2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. Configure your Environment Variables:
   Create a `.env` file in the `python/` directory and add your API keys:
   ```env
   GEMINI_API_KEY="your_api_key_here"
   BACKEND_URL="http://127.0.0.1:8000"
   # FIREBASE_CREDENTIALS="..." # Optional
   ```

### Running the System Locally

To run the full decoupled stack, you will need two terminal windows.

**Terminal 1 (Backend API & Daemon):**
```bash
cd python
source .venv/bin/activate
uvicorn api:app --reload
```
*Note: The `api.py` script automatically spins up the background `daemon.py` thread on startup.*

**Terminal 2 (Frontend Control Tower):**
```bash
cd python
source .venv/bin/activate
streamlit run app.py
```

Now, navigate to `http://localhost:8501` to access the Control Tower!

## 🧪 Testing

To run the unit test suite (with Firebase disabled to ensure testing in isolation):
```bash
cd python
source .venv/bin/activate
pytest test_memory.py
```

## 🤝 Built With

* [Google GenAI (Gemini 2.5 Flash)](https://ai.google.dev/)
* [FastAPI](https://fastapi.tiangolo.com/)
* [Streamlit](https://streamlit.io/)
* [PyDeck](https://deckgl.readthedocs.io/)
