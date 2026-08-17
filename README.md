# QueryMind AI

Enterprise Text-to-SQL copilot for the NovaMart retail database. Ask questions in plain English and get validated, read-only SQL results with natural-language explanations.

---

## Features

- **Natural-language queries** — converts plain English into PostgreSQL SELECT statements
- **Intent classification** — deterministic rules + LLM fallback to route CLEAR / AMBIGUOUS / UNSUPPORTED questions
- **Clarification flow** — asks follow-up questions when intent is ambiguous, then resumes the pipeline
- **RAG schema retrieval** — ChromaDB + fastembed retrieve the most relevant table docs before SQL generation
- **AST-based SQL validation** — sqlglot validates syntax, tables, columns, JOIN relationships, and blocks all write operations
- **Read-only execution** — PostgreSQL `transaction_read_only`, statement timeout, lock timeout, and a 100-row cap
- **Natural-language answers** — Groq LLM explains the result in plain English
- **Query history** — all queries persisted to PostgreSQL with status, SQL, row count, and duration
- **Bar chart visualization** — automatic chart rendering for numeric result sets
- **API key authentication** — all endpoints protected via `X-API-Key` header
- **Rate limiting** — 30 requests per 60 seconds per IP

---

## Architecture

```
User
 │
 ▼
React Frontend (Vite)
 │  axios + X-API-Key
 ▼
FastAPI Backend
 ├── Intent Classifier  ──► AMBIGUOUS ──► Clarification flow
 │       │
 │    CLEAR
 │       │
 ├── SQL Generator
 │    ├── Deterministic SQL (common queries, no LLM)
 │    └── RAG retrieval → ChromaDB → Groq LLM
 │       │
 ├── SQL Validator (sqlglot AST)
 │       │
 ├── SQL Executor (read-only PostgreSQL)
 │       │
 └── Answer Generator (Groq LLM)
         │
         ▼
    JSON response + history saved to PostgreSQL
```

---

## Database Schema (NovaMart)

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
# Edit .env with your DATABASE_URL, GROQ_API_KEY, and API_KEY
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
cp .env.example .env   # or edit .env directly
# Set VITE_API_BASE_URL and VITE_API_KEY
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173).

---

## Docker

```bash
# Copy and fill in backend env
cp backend/.env.example backend/.env

# Set your API key for the frontend
export VITE_API_BASE_URL=http://localhost:8000

docker compose up --build
```

- Backend: [http://localhost:8000](http://localhost:8000)
- Frontend: [http://localhost:5173](http://localhost:5173)
- API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## Environment Variables

### Backend (`backend/.env`)

| Variable | Description |
|---|---|
| `DATABASE_URL` | PostgreSQL async connection string (`postgresql+asyncpg://...`) |
| `GROQ_API_KEY` | Groq API key |
| `API_KEY` | Secret key required in `X-API-Key` header for all protected endpoints |

### Frontend (`frontend/.env`)

| Variable | Description |
|---|---|
| `VITE_API_BASE_URL` | Backend base URL (e.g. `http://localhost:8000`) |
| `VITE_API_KEY` | Must match the backend `API_KEY` |

---

## API Reference

All endpoints except `/` and `/health` require the `X-API-Key` header.

### Query

| Method | Path | Description |
|---|---|---|
| `POST` | `/query/` | Submit a natural-language question |
| `POST` | `/query/clarify` | Submit a clarification answer |
| `GET` | `/query/history` | List recent query history (`?limit=50`) |
| `GET` | `/query/history/{id}` | Get a single history record |

**POST /query/ — request**
```json
{ "question": "What are the top 5 products by revenue?" }
```

**POST /query/ — response (success)**
```json
{
  "status": "query_executed",
  "question": "What are the top 5 products by revenue?",
  "sql": "SELECT p.product_name, SUM(...) AS revenue FROM ...",
  "validation": { "valid": true, ... },
  "row_count": 5,
  "rows": [...],
  "answer": "The top 5 products by revenue are ..."
}
```

**POST /query/ — response (clarification required)**
```json
{
  "status": "clarification_required",
  "conversation_id": "uuid",
  "question": "What would you like to see for sales?",
  "options": ["Revenue", "Orders", "Product sales"]
}
```

### Other endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `GET` | `/schema/` | Live database schema |
| `POST` | `/rag/index` | Index schema into ChromaDB |
| `POST` | `/rag/search` | Search schema by question |
| `POST` | `/sql/generate` | Generate SQL without executing |
| `POST` | `/validation/validate` | Validate a SQL string |
| `GET` | `/database/test` | Test database connectivity |

---

## Example Queries

```
How many customers are there?
What is the total revenue?
Show me the top 10 products by revenue.
Which stores are in each region?
How many orders were placed in 2025?
What products are in each category?
Show me sales.                          ← triggers clarification
What is the employee happiness score?   ← unsupported
```

---

## Running Tests

```bash
# Unit tests only (no database required)
pytest tests/unit -v

# All tests (requires live database)
pytest tests/ -v
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI, SQLAlchemy (async), asyncpg |
| LLM | Groq (`llama-3.3-70b-versatile`) |
| SQL parsing | sqlglot |
| Vector store | ChromaDB |
| Embeddings | fastembed (`all-MiniLM-L6-v2`) |
| Frontend | React 19, Vite, Recharts, Lucide |
| Database | PostgreSQL |
| Container | Docker, Docker Compose |
