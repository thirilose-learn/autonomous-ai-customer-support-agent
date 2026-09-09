# Autonomous AI Customer Support & Resolution Agent

An AI-powered e-commerce customer support system that combines structured business data retrieval, policy-based RAG, and safe human escalation fallback.

## Architecture & Technology Stack

- **Frontend:** React + Vite (Vanilla CSS design system with responsive dark mode)
- **Backend:** FastAPI (Python 3.12, Pydantic v2, Uvicorn)
- **AI / Orchestration:** LangChain (Tools & Agents — Level 6+)
- **Knowledge Ingestion & RAG:** LlamaIndex (Level 4+)
- **Database & Vector Search:** Supabase PostgreSQL + `pgvector` (Level 3+)
- **Structured Data:** Brazilian E-Commerce Dataset (Olist)
- **Support Intent Taxonomy:** Bitext Customer Support Dataset
- **Voice-to-Text:** Whisper (Level 11+)

---

## Directory Structure

```text
capstone project/
├── dataset/                     # Source datasets (Olist & Bitext CSVs)
├── project details/             # Capstone project charter PDF
├── backend/                     # FastAPI backend application
│   ├── app/
│   │   ├── api/v1/              # Versioned API routes & endpoints
│   │   ├── core/                # App configuration (pydantic-settings)
│   │   ├── models/              # SQLAlchemy / DB models (Level 3)
│   │   ├── schemas/             # Request & response schemas
│   │   ├── services/            # Core business services
│   │   ├── database/            # Supabase connection client (Level 3)
│   │   ├── agents/              # LangChain agent workflow (Level 6)
│   │   ├── rag/                 # LlamaIndex retrieval pipeline (Level 4)
│   │   └── main.py              # FastAPI app entry & CORS setup
│   ├── tests/                   # Pytest automated test suite
│   ├── requirements.txt         # Pinned & verified Python dependencies
│   └── .env.example             # Backend environment template
├── frontend/                    # React + Vite application
│   ├── src/
│   │   ├── components/          # UI components (Header, Chat, Input, StatusBadge)
│   │   ├── services/            # API client (calls /api/health)
│   │   ├── index.css            # Custom CSS design system
│   │   └── App.jsx              # Main application shell
│   ├── package.json             # NPM dependencies
│   └── .env.example             # Frontend environment template
├── knowledge_base/              # Markdown policy documents (Level 4)
├── scripts/                     # Data cleaning & migration scripts (Level 2+)
├── .gitignore                   # Ignores venv, node_modules, .env secrets
└── README.md                    # Project overview & execution guide
```

---

## Quickstart & Local Development

### 1. Backend Setup & Execution

From the project root directory:

```powershell
# 1. Activate the dedicated virtual environment
.\backend\.venv\Scripts\Activate.ps1

# 2. Verify Python & Pip point to backend/.venv
python --version
python -m pip --version

# 3. (Optional) Install dependencies if setting up on a new machine
python -m pip install -r backend/requirements.txt

# 4. Run automated tests
python -m pytest backend/tests -v

# 5. Launch FastAPI development server
cd backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The API will be available at:
- **API Health:** `http://127.0.0.1:8000/api/health`
- **Swagger Docs:** `http://127.0.0.1:8000/api/v1/docs`

---

### 2. Frontend Setup & Execution

In a separate terminal:

```powershell
# 1. Navigate to frontend directory
cd frontend

# 2. Install dependencies (if first time)
npm install

# 3. Start Vite dev server
npm run dev
```

The frontend will run at:
- **Web UI:** `http://localhost:5173` (or `http://127.0.0.1:5173`)
