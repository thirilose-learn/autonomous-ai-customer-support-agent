# Autonomous AI Customer Support & Resolution Agent

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB.svg)](https://react.dev/)
[![Vite](https://img.shields.io/badge/Vite-5.4+-646CFF.svg)](https://vitejs.dev/)
[![LangChain](https://img.shields.io/badge/LangChain-0.3+-green.svg)](https://www.langchain.com/)
[![Supabase](https://img.shields.io/badge/Supabase-PostgreSQL%20%2B%20pgvector-3ECF8E.svg)](https://supabase.com/)
[![Groq](https://img.shields.io/badge/Groq-Cloud%20LLM%20Inference-F55036.svg)](https://groq.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

An autonomous, context-aware AI customer support and resolution application built for e-commerce platforms. The system combines structured relational business data retrieval, semantic policy retrieval-augmented generation (RAG), speech-to-text input (Whisper), strict cross-customer data isolation, and an intelligent human supervisor escalation workflow with automated ticket creation.

---

## Screenshots

| Main Interface | Order & Product Inquiry | Human Escalation |
| :---: | :---: | :---: |
| ![Main Interface](screenshots/01-main-interface.png) | ![Order & Product Inquiry](screenshots/02-order-and-product-inquiry.png) | ![Human Escalation](screenshots/03-human-escalation.png) |
| *Customer persona selection, quick inquiry pills, and responsive chat interface* | *Structured order items, English product category, pricing, and freight retrieval* | *Substantive issue review, multi-order disambiguation, and real support ticket creation* |

---

## 1. Problem Statement & Business Context

Customer support teams for e-commerce stores handle large volumes of repetitive inquiries regarding order tracking, delivery timelines, product specifications, returns, refunds, payment methods, and company policies. Standard chatbot approaches fail in production for three primary reasons:
1. **Lack of Business Grounding:** Generic LLMs hallucinate orders, items, tracking timelines, or return windows because they lack secure access to the store's operational database.
2. **Security & Privacy Risks:** Inadequately secured conversational systems risk exposing Customer A's private purchase history to Customer B.
3. **Premature Escalation vs. Deadlock:** Basic bots either escalate immediately without investigating or trap customers in unhelpful loops without providing human supervisor review when business rules cannot resolve the dispute.

This application implements an autonomous agent architecture that securely bridges customer identity, structured relational databases, policy knowledge bases, and human escalation queues.

---

## 2. Core Objectives

- **Intent Recognition & Query Routing:** Accurately classify customer requests into order inquiries, payment lookups, policy questions, supervisor requests, or general dialogue.
- **Autonomous Business Data Retrieval:** Inspect customer orders, order items, product categories, prices, freight charges, and payment breakdowns directly from relational database tables.
- **Policy RAG Grounding:** Retrieve verified return, refund, cancellation, shipping, and warranty rules via pgvector semantic search to eliminate policy hallucinations.
- **Strict Cross-Customer Isolation:** Enforce customer identity at the backend API layer using cryptographically signed session tokens; never allow the LLM or user to query another customer's data.
- **Intelligent Escalation & Disambiguation:** Differentiate between generic requests for a human, ambiguous multi-order complaints, and verified actionable issues. Gather required order context and contact info before creating persistent support tickets.
- **Multi-Modal Accessibility:** Provide text and voice input (Whisper speech-to-text) in a modern, responsive React interface.

---

## 3. System Architecture

```text
 ┌──────────────────────────────────────────────────────────────────┐
 │                      React 18 + Vite Frontend                    │
 │    - Persona Selector & Token Storage    - Quick Inquiry Bar     │
 │    - Voice Input (Whisper STT)           - Real-Time Chat UI     │
 └─────────────────────────────────┬────────────────────────────────┘
                                   │ HTTP / JSON (Bearer JWT)
                                   ▼
 ┌──────────────────────────────────────────────────────────────────┐
 │                     FastAPI Application Backend                  │
 │    - Cryptographic Session Verification (CustomerContext)        │
 │    - Speech-to-Text Transcription Service                        │
 │    - Intent Classification & Session Memory Management           │
 └─────────────────────────────────┬────────────────────────────────┘
                                   │
                                   ▼
 ┌──────────────────────────────────────────────────────────────────┐
 │                 Autonomous AI Agent (LangChain)                  │
 │    - Hosted LLM: Groq Developer Tier (gpt-oss-120b / 20b)        │
 │    - Multi-Turn Dialogue Memory with Escalation Boundary Reset   │
 │    - Response Precision Directives & Operational Guardrails      │
 └───────┬───────────────────┬──────────────────────┬───────────────┘
         │                   │                      │
         ▼                   ▼                      ▼
┌──────────────────┐┌──────────────────┐┌───────────────────────────┐
│ Customer Tools   ││  Policy RAG Tool ││  Human Escalation Tool    │
│ - get_my_orders  ││  (pgvector + BGE)││ - Reason Validation       │
│ - get_order_items││ - Return Policy  ││ - Order Disambiguation    │
│ - get_payments   ││ - Refund Policy  ││ - Contact Verification    │
│ (Enforces Owner) ││ - Shipping Policy││ - Supabase Persistence    │
└────────┬─────────┘└────────┬─────────┘└───────────┬───────────────┘
         │                   │                      │
         ▼                   ▼                      ▼
 ┌──────────────────────────────────────────────────────────────────┐
 │                   Supabase PostgreSQL Database                   │
 │    - Relational Olist Schema: customers, orders, order_items,    │
 │      products, order_payments                                    │
 │    - Vector Store: knowledge_embeddings (pgvector cosine search) │
 │    - Support Queue: support_escalations (persistent tickets)     │
 └──────────────────────────────────────────────────────────────────┘
```

---

## 4. Key Features

- **Authenticated Demo Personas:** Switch seamlessly between 5 diverse customer personas (VIP repeat buyers, multi-order customers, single-order users) to verify strict data isolation.
- **Customer-Scoped Order Tracking:** Live lookup of order status, purchase timestamps, estimated delivery dates, and real delivery timestamps.
- **Granular Product & Item Breakdown:** Retrieval of items within orders, including English product categories, unit prices, freight charges, product dimensions, and weights.
- **Payment Method Auditing:** Inspection of payment types (credit card, voucher, boleto), installment plans, and total payment amounts.
- **Semantic Knowledge Base RAG:** Local BAAI/bge-small-en-v1.5 embeddings and pgvector cosine similarity search across 6 company policy documents.
- **Intelligent Escalation Management:**
  - **Case A (Generic Human Request):** Asks what issue or order needs help without prematurely demanding contact info.
  - **Case B (Order Disambiguation):** Automatically detects multi-order customers and requires order ID, order date, or product details before creating a ticket.
  - **Case C (Contact Before Issue):** Acknowledges customer contact details and asks for issue specifics.
  - **Case D (Actionable Escalation):** Automatically creates a real ticket (`ESC-XXXXXXXX`), links customer contact info and affected order ID, and stores it in Supabase.
  - **De-Contamination Boundary:** Prevents past escalation tickets from hijacking future unrelated turns (e.g. asking for latest order items or payment methods after an escalation).
- **Speech-to-Text Input:** Integrated Whisper audio transcription endpoint for voice inquiries.
- **Truthful Non-Existent Product Handling:** Defends against brand hallucinations (e.g., Nike, Sony) by verifying against actual database records.

---

## 5. Technology Stack

| Component | Technology / Library | Version / Specification |
| :--- | :--- | :--- |
| **Backend Framework** | FastAPI | >= 0.115.0 |
| **Server Engine** | Uvicorn (ASGI) | >= 0.30.0 |
| **Agent Orchestration** | LangChain | >= 0.3.0 |
| **LLM Provider** | Groq Cloud Developer Tier | `openai/gpt-oss-120b` (Primary), `openai/gpt-oss-20b` (Fallback) |
| **Embeddings Model** | HuggingFace `BAAI/bge-small-en-v1.5` | 384-dimensional dense vectors (100% offline & free) |
| **Database & Vector Store**| Supabase PostgreSQL | PostgreSQL 15+ with `pgvector` extension |
| **Speech Recognition** | OpenAI Whisper API | High-accuracy multi-lingual voice transcription |
| **Frontend Framework** | React + Vite | React 18, Vite 5.4+ |
| **Frontend Styling** | Vanilla CSS Design Tokens | Custom dark mode, responsive glassmorphism |
| **Testing Suite** | Pytest + Starlette TestClient | 92 automated tests (34 core + 58 agent tests) |

---

## 6. Datasets & Knowledge Base

### 1. Bitext Customer Support Dataset
- **File:** `Dataset/Bitext_Sample_Customer_Support_Training_Dataset_27K_responses-v11.csv`
- **Processed:** `processed_data/bitext/customer_support_intents.csv`
- **Role:** Intent taxonomy and training benchmarks covering order inquiries, cancellations, refunds, returns, and support escalation triggers.

### 2. Olist Brazilian E-Commerce Dataset
- **Tables Ingested in Supabase:**
  - `customers`: Customer identifier, unique ID, zip code, city, and state.
  - `orders`: Order ID, customer ID, order status, purchase, approval, carrier, and delivery timestamps.
  - `order_items`: Order ID, item sequence ID, product ID, seller ID, price, freight value.
  - `products`: Product ID, category names (Portuguese + English translation), dimensions, weight.
  - `order_payments`: Order ID, sequential payment index, payment type, installments, payment value.
- **Data Integrity:** All foreign key relationships (`customer_id`, `order_id`, `product_id`) verified with 100% referential integrity.

### 3. Company Policy Knowledge Base
- **Directory:** `knowledge_base/`
- **Documents:**
  - `return_policy.md`: 7-day statutory right of withdrawal, 30-day defective return window, condition rules.
  - `refund_policy.md`: Inspection windows (3-5 business days), credit card statement cycles, bank transfer timelines.
  - `cancellation_policy.md`: Pre-shipment cancellation rules, in-transit refusal protocols.
  - `shipping_policy.md`: Delivery estimates, carrier tracking, lost shipment replacement guarantees.
  - `warranty_policy.md`: 90-day statutory warranty on durable goods, manufacturer claims.
  - `faqs.md`: Common customer service questions and direct answers.

---

## 7. Security & Customer Data Isolation

Strict customer isolation is guaranteed through multiple defensive layers:
1. **Cryptographic Session Tokens:** When a customer selects a persona, the backend issues an HMAC-SHA256 signed JWT containing only their immutable `demo_customer_id` and `customer_unique_id`.
2. **Server-Derived Context:** The AI agent and tools **never** accept `customer_id` from user prompts or LLM generated parameters. Identity is strictly injected from the verified session context.
3. **Database-Level Ownership Binding:** All customer data lookup functions enforce `.eq("customer_unique_id", customer.customer_unique_id)`. Even if an order ID belonging to Customer B is queried by Customer A, the database query returns `not found`.
4. **Zero Credentials in Version Control:** Environment secrets (`.env`) are strictly ignored by `.gitignore`.

---

## 8. Project Structure

```text
autonomous-ai-customer-support-agent/
├── .env.example                               # Root environment variable template
├── .gitignore                                 # Git ignore definitions
├── LICENSE                                    # MIT License
├── README.md                                  # Comprehensive project documentation
├── screenshots/                               # Application screenshots for documentation
│   ├── 01-main-interface.png
│   ├── 02-order-and-product-inquiry.png
│   └── 03-human-escalation.png
├── Dataset/                                   # Frozen source CSV datasets (Olist & Bitext)
├── Project Details/                           # Architecture specifications & PDF overview
├── backend/
│   ├── .env.example                           # Backend configuration template
│   ├── requirements.txt                       # Pinned Python dependencies
│   ├── app/
│   │   ├── main.py                            # FastAPI app, CORS, lifespans
│   │   ├── agents/
│   │   │   ├── agent.py                       # LangChain agent reasoning & tool loop
│   │   │   ├── llm.py                         # ChatGroq model factory
│   │   │   ├── memory.py                      # Multi-turn conversation store
│   │   │   ├── prompts.py                     # Production system prompt & directives
│   │   │   └── tools/
│   │   │       ├── customer_tools.py          # Orders, items, payment tools
│   │   │       ├── escalation_tool.py         # Human escalation ticket creation
│   │   │       └── policy_tool.py             # Knowledge base pgvector search
│   │   ├── api/v1/endpoints/                  # Auth, chat, health, RAG endpoints
│   │   ├── core/                              # App config & JWT session handling
│   │   ├── database/                          # Supabase client & schema validation
│   │   ├── rag/                               # Embedding engine & vector store
│   │   ├── schemas/                           # Pydantic request/response contracts
│   │   └── services/                          # Customer data, escalation policy, sessions
│   └── tests/                                 # Automated Pytest regression suites (8 files)
├── frontend/
│   ├── .env.example                           # Frontend configuration template
│   ├── package.json                           # NPM dependencies
│   ├── vite.config.js                         # Vite build configuration
│   ├── public/                                # Favicon and SVG iconography
│   └── src/
│       ├── App.jsx                            # Main application shell
│       ├── index.css                          # Custom CSS design system
│       ├── components/                        # UI: ChatWindow, Header, MessageInput, etc.
│       └── services/api.js                    # API client with token & Whisper audio upload
├── knowledge_base/                            # Markdown policy documents for RAG
├── processed_data/                            # Cleaned datasets, reports, synthetic personas
├── scripts/                                   # Data pipelines, migration runners, bulk loaders
└── supabase/migrations/                       # Version-controlled PostgreSQL DDL scripts
```

---

## 9. Setup & Local Installation

### Prerequisites
- Python 3.12+
- Node.js 18+ and npm
- Active Supabase project (Free Tier) with `pgvector` enabled
- Groq Cloud API Key (Free Developer Tier)

### 1. Repository Setup & Environment Configuration
Clone the repository and prepare the configuration files:

```bash
# Clone the repository
git clone https://github.com/thirilose-learn/autonomous-ai-customer-support-agent.git
cd autonomous-ai-customer-support-agent

# Create environment configuration files from templates
cp .env.example backend/.env
cp frontend/.env.example frontend/.env
```

Edit `backend/.env` with your actual credentials:
```ini
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
DATABASE_URL=postgresql://postgres.your-project-id:your_password@aws-0-region.pooler.supabase.com:6543/postgres
SESSION_SECRET_KEY=generate_a_random_64_char_hex_string
GROQ_API_KEY=gsk_your_groq_api_key_here
```

### 2. Backend Installation & Execution
```powershell
# Create and activate Python virtual environment
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install required dependencies
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# Start the FastAPI server
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
- Swagger API Docs: `http://127.0.0.1:8000/api/v1/docs`
- Health Check: `http://127.0.0.1:8000/api/health`

### 3. Frontend Installation & Execution
In a separate terminal:
```powershell
cd frontend
npm install
npm run dev
```
- Application Web UI: `http://localhost:5173`

---

## 10. Automated Testing & Verification

The test suite validates database schemas, JWT token lifecycle, customer isolation defense, RAG semantic search, Whisper audio handling, and agent decision-making.

### Running the Deterministic Test Suite (Zero Groq Tokens Consumed)
```powershell
# Run core backend test suites (34 tests)
backend/.venv/Scripts/python.exe -m pytest backend/tests/test_data_validation.py backend/tests/test_database_schema.py backend/tests/test_demo_session.py backend/tests/test_health.py backend/tests/test_rag_pipeline.py backend/tests/test_supabase_connection.py backend/tests/test_whisper_transcription.py -v

# Run agent deterministic tests (58 tests)
backend/.venv/Scripts/python.exe -m pytest backend/tests/test_ai_agent.py -v
```
**Result: All tests pass cleanly in under 30 seconds with zero API rate-limit impact.**

### Building Frontend Production Bundle
```powershell
cd frontend
npm run build
```
**Result: Built cleanly in under 300ms with zero errors.**

---

## 11. Manual Verification Guide

Visit `http://localhost:5173` to test live functionality:

1. **Persona Switching & Isolation:**
   - Select **Customer 00001** (VIP buyer, 17 orders). Ask: *"What did I buy in my latest order?"*.
   - Switch to **Customer 00002** (9 orders). Ask: *"What did I buy in my latest order?"*.
   - Verify that Customer 00002's actual latest order returns 1 item (`Bed Bath & Table`) and Customer 00001's history does not bleed over.
2. **Product Details & Pricing:**
   - In Customer 00002, ask: *"What items are in order 826b47e4cd7bba4e4c6fa5485f898b74?"*.
   - Verify it returns both items: `Home Construction` (R$239.90) and `Furniture & Decor` (R$97.00).
3. **Escalation Precision & Order Disambiguation:**
   - In Customer 00001, ask: *"What did I buy in my latest order?"*.
   - Confirm agent identifies order `d3582fd5ccccd9cb229a63dfb417c86f` and its item (Construction Tools).
   - Send: *"My delivered order arrived severely damaged and I need a replacement. Email: customer.test@example.com"*.
   - Agent does **NOT** immediately escalate; it asks whether the issue concerns the order just discussed or a different order.
   - Reply: *"Yes, the order we just discussed"*.
   - Agent creates exactly one real Ticket ID (`ESC-XXXXXXXX`), attaching the contact email and affected order ID `d3582fd5ccccd9cb229a63dfb417c86f`.
4. **De-Contamination Verification:**
   - In the same thread after ticket creation, ask: *"What payment method was used for my orders?"*.
   - Agent answers payment methods directly; does **NOT** re-escalate or spawn a second ticket.
5. **Truthful Brand Defense:**
   - Ask: *"Do I have Nike shoes or Sony headphones in my orders?"*.
   - Agent truthfully clarifies that no such brands exist in account records without fabricating products.
6. **Voice Input (Whisper STT):**
   - Click the microphone icon, record a voice query (e.g., *"Where is my order?"*), and verify transcription and automated response.

---

## 12. Known Limitations

- **Groq Cloud Rate Limits:** Free Developer Tier keys enforce a 200,000 Tokens Per Day (TPD) quota. Heavy automated multi-turn testing should be managed with deterministic unit tests to preserve quota for live evaluation.
- **Olist Catalog Granularity:** The Olist dataset records products by category classifications, weights, and dimensions rather than consumer brand names. The agent formats categories into clean English (e.g. `Bed Bath & Table`).
- **Demo Persona Scope:** The current frontend supports 5 pre-configured demo personas (`DEMO_00001` through `DEMO_00005`) mapped from the Olist dataset to showcase different customer journey archetypes.

---

## 13. Author & License

Built and maintained by **Thirilose Jones Nithish R**.

This project is licensed under the terms of the [MIT License](LICENSE).
