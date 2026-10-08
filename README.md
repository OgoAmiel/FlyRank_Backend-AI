# FlyRank Backend & AI Engineering

A collection of backend engineering systems built with **Python and FastAPI**, covering REST API development, PostgreSQL persistence, authentication, LLM integration, background job processing, web scraping, evaluation, and containerized development.

The repository was developed as part of practical backend and AI engineering work and contains several focused systems demonstrating different backend concepts.

## Systems Included

| System | Purpose | Main Technologies |
|---|---|---|
| Task API | RESTful task management and persistence | FastAPI, PostgreSQL, SQLModel |
| Authentication | User authentication and protected routes | Supabase, Bearer Tokens |
| AI Triage | Customer-support message classification | FastAPI, Pydantic, LLM APIs |
| LLM Evaluation | Evaluate triage classification behavior | Python, JSON |
| Background Jobs | Asynchronous report processing | FastAPI, Inngest |
| Web Scraper | Structured web data extraction pipeline | Python, BeautifulSoup, Pydantic |
| Infrastructure | Containerized application and database | Docker, Docker Compose |

---

## Architecture Overview

```text
FlyRank Backend & AI
│
├── FastAPI APIs
│   ├── Task API
│   │   ├── Service Layer
│   │   ├── Repository Layer
│   │   └── PostgreSQL
│   ├── Authentication
│   └── Protected Routes
│
├── AI Systems
│   ├── AI Triage
│   ├── Evaluation
│   └── Observability
│
├── Data Processing
│   ├── Web Scraper
│   └── Validation
│
└── Background Processing
    └── Inngest event-driven report jobs
```

---

# 1. Task Management REST API

The task API demonstrates a layered backend architecture using FastAPI, SQLModel, and PostgreSQL.

The application separates HTTP routing, business logic, persistence, and database models.

```text
HTTP Request
     ↓
FastAPI Route
     ↓
TaskService
     ↓
TaskRepository
     ↓
PostgresRepository
     ↓
PostgreSQL
```

### Features

- Create tasks
- Retrieve all tasks
- Retrieve an individual task
- Update tasks
- Delete tasks
- Input validation
- HTTP error handling
- PostgreSQL persistence
- Database initialization during application startup

### Endpoints

```http
GET    /tasks/
GET    /tasks/{task_id}
POST   /tasks/
PUT    /tasks/{task_id}
DELETE /tasks/{task_id}
```

The repository pattern separates database operations from business logic, allowing the service layer to depend on the `TaskRepository` abstraction rather than database-specific code.

---

# 2. Authentication & Protected Routes

Authentication is handled using **Supabase Auth**.

The API supports:

- User registration
- User login
- Bearer-token authentication
- Token validation
- Protected endpoints
- Logout

### Authentication Flow

```text
User Login
    ↓
Supabase Authentication
    ↓
Access Token
    ↓
Authorization: Bearer <token>
    ↓
FastAPI HTTPBearer
    ↓
Token Validation
    ↓
Protected Endpoint
```

Example routes include:

```http
POST /auth/signup
POST /auth/login
POST /auth/logout

GET /public/info
GET /protected/profile
GET /protected/dashboard
```

Invalid, missing, or expired authentication tokens return an HTTP `401 Unauthorized` response.

---

# 3. AI Customer-Support Triage

The repository includes an LLM-powered customer-support triage API that classifies incoming messages by category and urgency.

```http
POST /triage/
```

### Request

```json
{"text": "I was charged twice for my subscription."}
```

### Example Response

```json
{
  "category": "billing",
  "urgency": "normal",
  "confidence": 0.94,
  "reason": "The customer reports a duplicate subscription charge."
}
```

The confidence and reason are model-generated and can vary across requests.

### Classification Labels

| Category | Meaning |
|---|---|
| `billing` | Payments, subscriptions, invoices, charges, and refunds |
| `bug` | Clearly described errors, crashes, timeouts, or broken functionality |
| `feature` | Requests for new capabilities or product improvements |
| `other` | General inquiries, ambiguous messages, or unrelated requests |

| Urgency | Meaning |
|---|---|
| `low` | Vague requests, general inquiries, or unclear issues |
| `normal` | Standard billing issues, noncritical bugs, and ordinary feature requests |
| `high` | Critical problems such as repeated crashes, login failures, or major service disruptions |

The model selects category and urgency independently. Pydantic validates the response before the API returns it.

### Manually Test the Triage Endpoint (PowerShell)

With FastAPI and Ollama running, execute:

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/triage/" -Method POST -ContentType "application/json" -Body '{"text":"I was charged twice for my subscription."}'
```

To test a critical bug:

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/triage/" -Method POST -ContentType "application/json" -Body '{"text":"The app crashes every time I try to log in."}'
```

The expected labels for the second example are `bug` and `high`.

---

## LLM Reliability

The triage service includes safeguards around model calls and model-generated responses.

### Timeout Handling

Model calls use a configured request timeout to avoid waiting indefinitely. The local evaluation was also run with an increased evaluator timeout.

### Selective Retries

Timeouts, connection failures, HTTP `429`, and HTTP `5xx` responses can trigger retries with increasing delays and jitter. HTTP `400`, `401`, and `403` responses are not blindly retried.

### Structured Output Validation and Repair

The service extracts JSON (including from some responses with surrounding text or Markdown fences), then validates it against the `TriageOutput` Pydantic schema. If the first response fails validation, the service requests one corrected response. If the repair also fails, it records the outputs in a quarantine log.

```text
LLM response
     |
     v
Extract JSON and validate with Pydantic
     |
     +-- Valid --> Return structured result
     |
     +-- Invalid --> One repair request
                         |
                         v
                    Validate again
                         |
                         +-- Valid --> Return result
                         +-- Invalid --> Quarantine log
```

---

## LLM Configuration

The OpenAI-compatible Python client is configured through environment variables, so compatible providers can be used without rewriting the service. Local development and evaluation used Ollama with `llama3.2:3b`.

```env
LLM_BASE_URL=http://host.docker.internal:11434/v1
LLM_API_KEY=your_local_api_key
LLM_MODEL=llama3.2:3b
LLM_STUB=0
LLM_ENABLED=true
```

The `host.docker.internal` address lets the application container reach Ollama on the Windows host. Store real secrets only in the ignored `.env` file. Start Ollama and download the model if needed:

```powershell
ollama pull llama3.2:3b
```

### Prompt Versioning

```text
prompts/
├── triage-v1.md
└── triage-v2.md
```

The active prompt is selected in `llm/triage_service.py`:

```python
PROMPT_PATH = ROOT_DIR / "prompts" / "triage-v2.md"
PROMPT_VERSION = "triage-v2"
```

Version 2 adds explicit category definitions, urgency rules, ambiguity handling, and instructions to treat customer messages as untrusted data. The active version was verified inside Docker using:

```powershell
docker compose exec app python -c "from llm.triage_service import get_prompt_version; print(get_prompt_version())"
```

Recorded output: `triage-v2`.

---

# 4. LLM Evaluation

The `evals/` directory contains a labeled development evaluation set and a script that submits each case to the live `/triage/` endpoint.

```text
evals/
├── cases.json
└── run_eval.py
```

The eight cases cover billing, refunds, bugs, feature requests, vague messages, and prompt-injection attempts. Each case specifies an expected category and urgency.

### Run the Evaluation

Ensure Docker, FastAPI, and Ollama are running. From the project directory:

```powershell
python evals\run_eval.py
```

### Recorded Results — 8 October 2026

| Metric | Prompt V1 baseline | Prompt V2 |
|---|---:|---:|
| Category matches | 6/7 (85.7%) | **8/8 (100.0%)** |
| Urgency matches | 4/7 (57.1%) | **8/8 (100.0%)** |
| Successful requests | 7/8 | **8/8** |
| Request failures | 1 | **0** |

The match-rate denominator is successful requests, not all eight cases. The recorded V2 evaluation printed:

```text
=== AI TRIAGE EVALUATION ===
Total cases: 8
Successful requests: 8/8
Request failures: 0
Category matches: 8/8 (100.0%)
Urgency matches: 8/8 (100.0%)

Mismatches and errors:
none
```

**Limitations:** Eight cases are too few to establish production accuracy. Some V2 prompt examples closely resemble evaluation cases, so this is not an independent holdout test. Timeouts also differed between runs, limiting direct comparison of request reliability. Future work should evaluate unseen cases across repeated runs and measure latency.

### Automated Tests

The project also has a separate pytest suite, previously recorded at **38 passing tests**, including mocked AI triage tests. These tests verify application behavior and are not a substitute for live model evaluation.

```powershell
python -m pytest -v
```

The repository also uses GitHub Actions for CI testing.

---

# 5. LLM Observability

Model calls record operational metadata, including timestamp, prompt version, model, reported input/output token counts, request duration, and whether a repair attempt was used.

```text
logs/
├── cost.jsonl
└── quarantine.jsonl
```

`cost.jsonl` stores usage and latency metadata (not calculated monetary cost). `quarantine.jsonl` stores model outputs that still fail validation after repair, along with diagnostic information. Logs can help identify slow calls, provider failures, and invalid model responses.

---

# 6. Background Job Processing

A separate FastAPI application under `jobs_api/` demonstrates asynchronous and event-driven processing using **Inngest**.

Instead of forcing a user to wait for slow work to complete inside an HTTP request, the API accepts the request and creates a background job.

### Report Flow

```text
POST /reports
      ↓
Generate Report ID
      ↓
Store Pending State
      ↓
Send report/requested Event
      ↓
Return 202 Accepted
      ↓
Inngest Worker
      ↓
Process Report
      ↓
Done / Failed
```

The client can poll:

```http
GET /reports/{report_id}
```

to retrieve the current state.

Possible states include:

```text
pending
done
failed
```

The example intentionally simulates slow processing to demonstrate why background jobs are useful for operations that should not block HTTP requests.

### Reliability

The background workflow demonstrates:

- Event-driven processing
- Asynchronous execution
- Retry configuration
- Failure handling
- Status tracking
- Polling
- Eventual consistency

The report store is currently in-memory and is intended as a demonstration rather than persistent production storage.

---

# 7. Scheduled Jobs

The background-job application also contains an Inngest heartbeat function.

The current development schedule runs once per minute:

```cron
* * * * *
```

The heartbeat reports the number of:

```text
pending
done
failed
```

report jobs.

This demonstrates scheduled background execution alongside event-triggered functions.

---

# 8. Web Scraping Pipeline

The `scraper/` directory contains a standalone Python scraping and data-processing pipeline.

The scraper uses the public **Books to Scrape** practice website and processes the first three catalogue pages.

### Pipeline

```text
Catalogue Pages
       ↓
Discover Book URLs
       ↓
Deduplicate URLs
       ↓
Fetch Product Pages
       ↓
Parse HTML
       ↓
Extract Fields
       ↓
Normalize Data
       ↓
Pydantic Validation
       ↓
Deduplicate Records
       ↓
Structured JSON Output
```

Extracted fields include:

```text
title
product_url
price_text
price_gbp
availability_text
rating_text
description
source_page
fetched_at
```

### Reliability Features

The scraper includes:

- Request timeouts
- Request throttling
- Cache-first fetching
- Retry handling
- Structured validation
- Data normalization
- URL deduplication
- Error recording
- Run reporting

Cached pages can be reused during development, reducing unnecessary requests to the source website.

### Outputs

```text
scraper/output/
├── books.json
├── errors.json
└── run-report.json
```

A recorded cached development run processed:

```text
60 valid records
0 invalid records
0 failed pages
```

The scraper intentionally avoids browser automation because the required information is available directly in the server-rendered HTML.

See `scraper/README.md` for additional implementation details.

---

# 9. Docker & PostgreSQL

The main FastAPI application and PostgreSQL database can be run using Docker Compose.

The environment contains:

```text
tasks_app → FastAPI application
tasks_db  → PostgreSQL 17
```

Start the environment with:

```bash
docker compose up -d --build
```

Check the containers:

```bash
docker compose ps
```

View application logs:

```bash
docker compose logs app
```

Stop the environment:

```bash
docker compose down
```

The FastAPI application is exposed on:

```text
http://localhost:8000
```

Interactive API documentation is available at:

```text
http://localhost:8000/docs
```

---

# Environment Configuration

Create a `.env` file using `.env.example` as a template.

```env
POSTGRES_DB=tasks_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=change_me
POSTGRES_HOST=db
POSTGRES_PORT=5432

PORT=8000

SUPABASE_URL=
SUPABASE_KEY=

LLM_BASE_URL=
LLM_API_KEY=
LLM_MODEL=
LLM_STUB=0
LLM_ENABLED=true
```

Real credentials should only be stored in `.env`, which is excluded from version control.

---

# Project Structure

```text
FlyRank_Backend-AI/
│
├── main.py
├── database.py
├── dependencies.py
├── models.py
├── schemas.py
│
├── routes/
│   ├── tasks.py
│   ├── auth.py
│   ├── protected.py
│   └── triage.py
│
├── services/
│   └── task_service.py
│
├── repositories/
│   ├── base.py
│   └── postgres_repository.py
│
├── llm/
│   ├── schemas.py
│   ├── hello.py
│   └── triage_service.py
│
├── prompts/
│   ├── triage-v1.md
│   └── triage-v2.md
│
├── evals/
│   ├── cases.json
│   └── run_eval.py
│
├── jobs_api/
│   └── main.py
│
├── scraper/
│   ├── src/
│   ├── cache/
│   ├── output/
│   └── README.md
│
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── .dockerignore
└── .gitignore
```

---

# Technology Stack

**Backend**

- Python
- FastAPI
- Pydantic
- SQLModel
- SQLAlchemy

**Database**

- PostgreSQL

**Authentication**

- Supabase Auth
- Bearer-token authentication

**AI**

- OpenAI-compatible Python client
- Ollama during local development
- Structured LLM output
- Prompt versioning
- Evaluation tooling

**Background Processing**

- Inngest

**Data Extraction**

- BeautifulSoup
- Requests

**Infrastructure**

- Docker
- Docker Compose

---

# Engineering Concepts Demonstrated

This repository demonstrates practical implementations of:

- REST API design
- Layered backend architecture
- Repository and service patterns
- Dependency injection
- Relational database persistence
- Authentication and authorization
- Structured LLM integration
- LLM output validation and repair
- Retry and timeout strategies
- AI evaluation and observability
- Event-driven architecture
- Background job processing
- Scheduled jobs
- Web scraping and data normalization
- Containerized development

---

## Project Status

This repository is an engineering learning and development project containing several focused backend systems rather than a single production application.

The implementations are intended to demonstrate backend architecture, reliability patterns, AI integration, data processing, and asynchronous application design.