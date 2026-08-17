# QueryMind AI

> Enterprise Text-to-SQL copilot — ask your NovaMart retail database questions in plain English and get validated, read-only SQL results with natural-language explanations.

**Live demo:** https://querymind-frontend-cyrb.onrender.com

---

## Screenshots

| Query input | Clarification flow | Results + chart |
|---|---|---|
| Type a natural-language question | QueryMind asks for clarification when intent is ambiguous | Results shown as table + bar chart with generated SQL |

> Screenshots can be added to `docs/screenshots/` and referenced here.

---

## Features

| Feature | Detail |
|---|---|
| Natural-language queries | Converts plain English into PostgreSQL SELECT statements |
| Intent classification | Deterministic rules + LLM fallback → CLEAR / AMBIGUOUS / UNSUPPORTED |
| Clarification flow | Asks follow-up questions when intent is ambiguous, then resumes |
| RAG schema retrieval | ChromaDB + fastembed retrieve relevant table docs before SQL generation |
| AST-based SQL validation | sqlglot validates syntax, tables, columns, JOINs, blocks all writes |
| Read-only execution | `transaction_read_only`, statement timeout, lock timeout, 100-row cap |
| Natural-language answers | Groq LLM explains results in plain English |
| Query history | All queries persisted to PostgreSQL with status, SQL, row count, duration |
| Bar chart visualization | Automatic chart rendering for numeric result sets |
| API key authentication | All endpoints protected via `X-API-Key` header |
| Rate limiting | 30 requests / 60 seconds per IP |
| Request tracing | `X-Request-ID` header on every response |
| Readiness probe | `/ready` returns 503 until database is reachable |

---

## Architecture

```
User
 │
 ▼
React Frontend (Vite + Recharts)
 │  axios  ·  X-API-Key header  ·  X-Request-ID
 ▼
FastAPI Backend
 │
 ├── Rate Limiter (30 req / 60 s per IP)
 │
 ├── Intent Classifier
 │    ├── Deterministic rules (fast path)
 │    └── Groq LLM fallback
 │         ├── CLEAR ──────────────────────────────────────┐
 │         ├── AMBIGUOUS ──► Clarification flow            │
 │         └── UNSUPPORTED ──► 200 unsupported response    │
 │                                                         │
 ├── SQL Generator ◄──────────────────────────────────────┘
 │    ├── Deterministic SQL (common queries, zero LLM cost)
 │    └── RAG retrieval → ChromaDB → Groq LLM
 │
 ├── SQL Validator (sqlglot AST)
 │    ├── Syntax check
 │    ├── Single-statement enforcement
 │    ├── SELECT-only enforcement
 │    ├── Table + column validation
 │    └── JOIN relationship validation
 │
 ├── SQL Executor (PostgreSQL, read-only)
 │    ├── transaction_read_only = true
 │    ├── statement_timeout = 5 s
 │    ├── lock_timeout = 3 s
 │    └── LIMIT capped at 100 rows
 │
 └── Answer Generator (Groq LLM)
          │
          ▼
     JSON response
          │
          ├── History saved to PostgreSQL (query_history table)
          └── X-Request-ID echoed in response headers
```

---

## Database Schema (NovaMart)

```
customers ──────────────────────────────────────────────────────────────────┐
    │ region_id → regions                                                    │
    │                                                                        │
orders ──────────────────────────────────────────────────────────────────── │
    │ customer_id → customers                                                │
    │ store_id    → stores                                                   │
    │                                                                        │
order_items                                                                  │
    │ order_id   → orders                                                    │
    │ product_id → products                                                  │
    │                                                                        │
products                                                                     │
    │ category_id → categories                                               │
    │ supplier_id → suppliers ──► region_id → regions                       │
    │                                                                        │
stores ──────────────────────────────────────────────────────────────────── │
    │ region_id → regions ◄──────────────────────────────────────────────── ┘
    │
employees
    │ store_id → stores

inventory  ·  payments  ·  shipments  ·  returns
```

| Table | Description |
|---|---|
| `customers` | Customer profiles, region, segment |
| `orders` | Purchase transactions |
| `order_items` | Line items per order |
| `products` | Product catalog |
| `categories` | Product categories |
| `suppliers` | Product suppliers |
| `stores` | Physical store locations |
| `regions` | Geographic regions |
| `inventory` | Stock levels per store |
| `payments` | Payment transactions |
| `shipments` | Delivery records |
| `returns` | Return and refund records |
| `employees` | Store employees |

---

## Quick Start

### Prerequisites

- Python 3.13+
- Node.js 22+
- PostgreSQL with the NovaMart database loaded
- A [Groq API key](https://console.groq.com)

### 1. Clone

```bash
git clone https://github.com/Nish12345944/Querymind-ai.git
cd querymind-ai
```

### 2. Backend

```bash
cd backend
cp .env.example .env
# Fill in DATABASE_URL, GROQ_API_KEY, API_KEY, and optionally FRONTEND_URL
pip install -r requirements.txt
uvicorn main:app --reload
```

### 3. Index the schema (first run only)

```bash
curl -X POST http://localhost:8000/rag/index \
  -H "X-API-Key: your_api_key_here"
```

### 4. Frontend

```bash
cd frontend
cp .env.example .env
# Set VITE_API_BASE_URL=http://localhost:8000
# Set VITE_API_KEY=your_api_key_here
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173).

---

## Docker

```bash
cp backend/.env.example backend/.env
# Fill in backend/.env

VITE_API_BASE_URL=http://localhost:8000 docker compose up --build
```

| Service | URL |
|---|---|
| Backend | http://localhost:8000 |
| Frontend | http://localhost:5173 |
| API docs | http://localhost:8000/docs |

---

## Environment Variables

### Backend (`backend/.env`)

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | Yes | `postgresql+asyncpg://user:pass@host:5432/db` |
| `GROQ_API_KEY` | Yes | Groq API key from console.groq.com |
| `API_KEY` | Yes | Secret key for `X-API-Key` header |
| `FRONTEND_URL` | No | Production frontend URL added to CORS allowlist |

### Frontend (`frontend/.env`)

| Variable | Required | Description |
|---|---|---|
| `VITE_API_BASE_URL` | Yes | Backend base URL |
| `VITE_API_KEY` | Yes | Must match backend `API_KEY` |

---

## API Reference

All endpoints except `GET /` , `GET /health`, and `GET /ready` require `X-API-Key`.

### Query endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/query/` | Yes + rate limit | Submit a natural-language question |
| `POST` | `/query/clarify` | Yes | Submit a clarification answer |
| `GET` | `/query/history` | Yes | List recent query history (`?limit=50`) |
| `GET` | `/query/history/{id}` | Yes | Get a single history record |

### System endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/health` | No | Liveness check |
| `GET` | `/ready` | No | Readiness check (503 if DB unavailable) |
| `GET` | `/schema/` | Yes | Live database schema |
| `POST` | `/rag/index` | Yes | Index schema into ChromaDB |
| `POST` | `/rag/search` | Yes | Search schema by question |
| `POST` | `/sql/generate` | Yes | Generate SQL without executing |
| `POST` | `/validation/validate` | Yes | Validate a SQL string |
| `GET` | `/database/test` | Yes | Test database connectivity |

### Request / Response

**POST /query/ — request**
```json
{ "question": "What are the top 5 products by revenue?" }
```

**POST /query/ — success response**
```json
{
  "status": "query_executed",
  "question": "What are the top 5 products by revenue?",
  "sql": "SELECT p.product_name, SUM(...) AS revenue FROM ...",
  "validation": { "valid": true, "checks": { ... } },
  "row_count": 5,
  "rows": [ { "product_name": "...", "revenue": 12345.67 } ],
  "answer": "The top 5 products by revenue are ..."
}
```

**POST /query/ — clarification required**
```json
{
  "status": "clarification_required",
  "conversation_id": "uuid",
  "question": "What would you like to see for sales?",
  "options": ["Revenue", "Orders", "Product sales"]
}
```

**POST /query/clarify — request**
```json
{
  "conversation_id": "uuid",
  "answer": "Revenue"
}
```

---

## Example Queries

```
How many customers are there?
What is the total revenue?
Show me the top 10 products by revenue.
Which stores are in each region?
How many orders were placed in 2025?
What products are in each category?
What is the average product price?
Show me sales.                          ← triggers clarification
What is the employee happiness score?   ← unsupported
```

---

## Running Tests

```bash
# Unit + security tests (no database required)
pytest tests/unit -v

# Integration tests (requires live database)
pytest tests/integration -v

# End-to-end tests (requires live database + Groq API key)
pytest tests/e2e -v

# All tests
pytest tests/ -v
```

---

## Project Structure

```
querymind-ai/
├── backend/
│   ├── app/
│   │   ├── api/          # FastAPI routers
│   │   ├── core/         # Config, security, rate limiting, logging
│   │   ├── db/           # SQLAlchemy engine + models
│   │   ├── schemas/      # Pydantic response models
│   │   └── services/     # Business logic pipeline
│   ├── main.py           # FastAPI app entrypoint
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── App.jsx       # Single-page React app
│       └── App.css
├── tests/
│   ├── unit/             # Fast, no DB required
│   ├── integration/      # Requires live DB
│   └── e2e/              # Full pipeline tests
├── docker-compose.yml
└── README.md
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI 0.114, SQLAlchemy 2 (async), asyncpg |
| LLM | Groq — `llama-3.3-70b-versatile` |
| SQL parsing | sqlglot 30 |
| Vector store | ChromaDB 1.5 |
| Embeddings | fastembed — `all-MiniLM-L6-v2` |
| Frontend | React 19, Vite 8, Recharts, Lucide |
| Database | PostgreSQL 16 |
| Container | Docker, Docker Compose |
| CI | GitHub Actions |

---

## Portfolio Notes

**What this demonstrates:**

- Full-stack AI application design — React frontend → FastAPI backend → PostgreSQL + ChromaDB
- RAG pipeline — schema documents embedded with fastembed, retrieved from ChromaDB, injected into LLM context
- Defense-in-depth SQL security — AST validation (sqlglot) + read-only DB transaction + statement timeout + row cap
- LLM orchestration — intent classification, SQL generation, and answer generation with Groq, with deterministic fast paths to reduce latency and cost
- Production patterns — structured logging, request tracing, readiness probes, rate limiting, API key auth, CORS configuration
- Test coverage — unit, integration, security, and end-to-end test suites

**LinkedIn description:**

> Built QueryMind AI, an enterprise Text-to-SQL copilot that converts natural-language questions into validated PostgreSQL queries against a 13-table retail database. The system uses a RAG pipeline (ChromaDB + fastembed) for schema retrieval, Groq LLM (llama-3.3-70b-versatile) for SQL generation and answer synthesis, and sqlglot AST validation to enforce read-only access. Stack: FastAPI, React 19, PostgreSQL, Docker.

**Resume bullets:**

- Designed and shipped a full-stack Text-to-SQL AI system (FastAPI + React) with RAG-powered schema retrieval, LLM-generated SQL, AST-based validation, and read-only PostgreSQL execution
- Implemented a multi-layer SQL security model: sqlglot AST validation, PostgreSQL `transaction_read_only`, statement/lock timeouts, and a 100-row result cap
- Built a clarification flow that detects ambiguous queries, collects user intent, and resumes the SQL generation pipeline with semantic business context
- Achieved sub-second response times for common queries via deterministic SQL fast paths that bypass LLM calls entirely
