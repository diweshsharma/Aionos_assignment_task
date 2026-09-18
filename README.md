# ✈️ AIONOS SkyAssist — Airline Disruption Resolution & Compensation Agent

> An autonomous, policy-compliant AI agent system designed to handle flight disruptions (delays, cancellations, rebooking, vouchers, and compensations) with multi-turn conversational memory, deterministic policy enforcement, authority guardrails, and a modern customer-first interface.

---

## 🌟 Overview

Airline disruptions are stressful for passengers and costly for customer operations. **AIONOS SkyAssist** bridges the gap between automated self-service and strict airline compliance by providing:

1. **Natural, Empathetic Customer Dialogue**: A customer-facing chat interface that delivers human-like conversational responses without form-letter templates or raw technical logs.
2. **Deterministic Policy Engine & RAG**: Combines vector retrieval (ChromaDB) for airline policy guidelines with a deterministic rules engine (`policy_engine.py`) to calculate accurate passenger entitlements based on delay duration and loyalty tier.
3. **Authority Guard & Supervisor Escalations**: Enforces strict agent limits (e.g. fare-difference waivers up to ₹1,500; hotel accommodation for delayed hours only). Any request exceeding agent limits, involving legal threats, or requesting non-standard payment methods is automatically flagged and logged for supervisor review.
4. **Auditability & Disruption Details Drawer**: Operational logs, customer profile metrics, and executed actions are neatly housed in a collapsible slide-over Details drawer (which auto-opens once on the first escalation for discoverability).

---

## 🏗️ Architecture

```mermaid
graph TD
    Client["React + Vite Frontend (Port 5173)"] <--> API["FastAPI Backend (Port 8000)"]
    API <--> Auth["PNR Auth & Lookup (/auth/lookup-pnr)"]
    API <--> Graph["LangGraph Workflow State Machine"]

    subgraph LangGraph Agent Pipeline
        N1["1. Extract Intents (Groq LLM / Keyword Fallback)"] --> N2["2. Lookup Booking (SQLite DB)"]
        N2 --> N3["3. Retrieve Policy Context (Chroma RAG)"]
        N3 --> N4["4. Evaluate Policy (Deterministic Engine)"]
        N4 --> N5["5. Authority Check (Guardrails & Limits)"]
        N5 --> N6["6. Execute Actions (Generate Vouchers/Offers)"]
        N6 --> N7["7. Escalate Items (Flag Supervisor Reviews)"]
        N7 --> N8["8. Draft Response (LLM / Conversational Builder)"]
        N8 --> N9["9. Log Turn (Persist Conversation History)"]
    end

    Graph <--> DB[("SQLite Database (airline_agent.db)")]
    Graph <--> Vector[("Chroma Vector DB")]
```

---

## ✨ Key Features & Capabilities

- **PNR-Based Authentication**: Secure passenger lookup via PNR (`SK4821X`, `TR1190B`, `WL7742`).
- **Proactive Welcome Greetings**: The agent immediately greets the passenger upon login referencing their actual flight details (e.g. *"Hi Meher, I can see flight SK-305 to Hyderabad is delayed 6 hours — sorry about the wait! How can I help?"*).
- **Multi-Turn Conversational Memory**: Passes prior turn history into agent state, allowing seamless follow-up questions (*"why can't you give full night?"*) without repeating previous summaries or re-running static actions.
- **Deterministic Delay & Cancellation Policy**:
  - **3h–5h Delay**: ₹500 Meal Voucher + Lounge Access.
  - **> 5h Delay**: ₹500 Meal Voucher + Lounge Access + Hotel Accommodation for delayed hours.
  - **Cancelled Flight**: Option for full refund to original payment or free rebooking.
  - **Fare Waiver Limit**: Agent approval up to ₹1,500; requests > ₹1,500 automatically escalate.
- **Collapsible Operational Details Panel**:
  - Main chat screen stays 100% customer-friendly (showing subtle inline `🚩 Escalated to a supervisor` tags).
  - Detailed operational logs (plain-language executed actions like `Meal Voucher Issued — ₹500` and customer profile data) are stored in a collapsible drawer toggled via the `Disruption Details` button.

---

## 📁 Repository Structure

```
ainos assignment/
├── backend/
│   ├── agent/                  # LangGraph state machine & 9 pipeline nodes
│   │   ├── graph.py            # LangGraph workflow definition
│   │   ├── nodes.py            # Node functions (intents, lookup, policy, authority, response)
│   │   └── state.py            # AgentState TypedDict schema
│   ├── routers/                # FastAPI endpoint routers
│   │   ├── admin.py            # Admin CRUD & CSV bulk import endpoints
│   │   ├── auth.py             # PNR authentication & lookup endpoints
│   │   └── chat.py             # Main POST /chat agent invocation endpoint
│   ├── services/               # Core business logic & LLM services
│   │   ├── authority_guard.py  # Guardrail limit checks & escalation logic
│   │   ├── booking_service.py  # Database CRUD for customers, bookings, & turns
│   │   ├── llm_client.py       # Groq LLM client + natural conversational fallback builder
│   │   ├── policy_engine.py    # Deterministic policy rules evaluator
│   │   └── rag_service.py      # ChromaDB vector retrieval for policy guidelines
│   ├── tests/                  # Pytest automated test suite (70 test cases)
│   ├── models.py               # SQLAlchemy ORM schemas
│   ├── policy_rules.yaml       # Master policy specification rules
│   ├── seed.py                 # Initial database seeder script
│   └── main.py                 # FastAPI application entrypoint
├── frontend/
│   ├── src/
│   │   ├── api/client.ts       # Axios API client wrappers
│   │   ├── components/         # React UI components
│   │   │   ├── ActionLogPanel.tsx  # Collapsible Details Drawer component
│   │   │   ├── AdminModal.tsx      # Admin management modal
│   │   │   ├── ChatWindow.tsx      # Customer chat window component
│   │   │   ├── CustomerBanner.tsx  # Flight status & passenger info banner
│   │   │   ├── Header.tsx          # App header & PNR switcher
│   │   │   └── LoginScreen.tsx     # PNR authentication screen with demo presets
│   │   ├── App.tsx             # Main React application shell
│   │   ├── main.tsx            # React DOM entrypoint
│   │   └── index.css           # Modern glassmorphism CSS design system
│   └── package.json            # Vite + React dependencies
├── .env.example                # Example environment variables template
└── README.md                   # End-to-end documentation
```

---

## 🚀 Quick Start Guide

### Prerequisites

- **Python**: 3.11 or higher
- **Node.js**: v18 or higher (with `npm`)

### 1. Backend Setup

1. **Navigate to the backend directory** (or root):
   ```bash
   cd backend
   ```

2. **Create and activate a virtual environment** (recommended):
   ```bash
   python -m venv venv
   # On Windows (PowerShell):
   .\venv\Scripts\Activate.ps1
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables**:
   Create a `.env` file in the project root (or copy `.env.example`):
   ```ini
   GROQ_API_KEY=your_groq_api_key_here
   AUTH_TOKEN=dev_secret_token_123
   DATABASE_URL=sqlite:///./airline_agent.db
   ```
   *(Note: If `GROQ_API_KEY` is not provided or invalid, the system automatically uses its deterministic natural conversational fallback generator.)*

5. **Seed the Database**:
   ```bash
   python seed.py
   ```

6. **Start the FastAPI Backend Server**:
   ```bash
   python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```
   - API Docs will be available at: [http://localhost:8000/docs](http://localhost:8000/docs)

---

### 2. Frontend Setup

1. **Navigate to the frontend directory**:
   ```bash
   cd ../frontend
   ```

2. **Install Node Dependencies**:
   ```bash
   npm install
   ```

3. **Start the Vite Development Server**:
   ```bash
   npm run dev
   ```
   - Frontend Application will be accessible at: [http://localhost:5173](http://localhost:5173)

---

## 🧪 Testing & Verification

### Running Backend Pytest Suite (70 Tests)

The backend includes a comprehensive unit and scenario test suite covering intent extraction, authority guardrails, policy engine logic, admin CRUD, PNR authentication, and multi-turn conversational memory.

Run all tests from the project root:
```bash
python -m pytest backend/tests/ -v
```

### Running Frontend Build Verification

To verify TypeScript compilation and bundle build:
```bash
cd frontend
npm run build
```

---

## 📋 Demo PNR Scenarios

Try the pre-seeded passenger scenarios directly on the login screen ([http://localhost:5173](http://localhost:5173)):

| PNR | Passenger Name | Loyalty Tier | Flight Disruption | Recommended Test Flow |
| :--- | :--- | :--- | :--- | :--- |
| **`SK4821X`** | Priya Sharma | Gold | **CANCELLED** (Flight SK-204) | 1. Ask for a full refund.<br>2. Ask for a free rebooking.<br>3. Demand a business class upgrade + cash (Triggers escalation). |
| **`TR1190B`** | Arvind Patel | Silver | **4.0h DELAY** (Flight TR-881) | 1. Ask what benefits apply.<br>2. Request a meal voucher & lounge pass.<br>3. Ask for a hotel room (Declined per policy; delay < 5h). |
| **`WL7742`** | Meher Kaur | Platinum | **6.0h DELAY** (Flight SK-305) | 1. Request meal, lounge, and hotel.<br>2. Ask for a full night hotel stay (Escalated to supervisor).<br>3. Ask for ₹2,000 fare waiver (Escalated: exceeds ₹1,500 limit). |

---

## 🛡️ Security & Git Compliance

- **Push Protection**: `.env`, SQLite databases (`airline_agent.db`), vector stores (`chroma_db/`), and build artifacts are strictly excluded from version control via `.gitignore`.
- **Bearer Authentication**: Backend endpoints require `Authorization: Bearer dev_secret_token_123` header for administrative security.

---

## 📄 License

Developed for the AIONOS AI Agent Assignment Task.
