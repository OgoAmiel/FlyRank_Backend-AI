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
        ┌───────────────────┼────────────────────┐
        │                   │                    │
    FastAPI APIs        AI Systems         Data Processing
        │                   │                    │
        ├─ Task API         ├─ AI Triage         ├─ Web Scraper
        ├─ Authentication   ├─ Evaluation        └─ Validation
        └─ Protected Routes └─ Observability
        │
        ├─ Service Layer
        ├─ Repository Layer
        └─ PostgreSQL

                Background Processing
                        │
                      Inngest
                        │
              Event-driven report jobs
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

The repository includes an LLM-powered customer-support triage API.

```http
POST /triage/
```

The service classifies incoming support messages using two dimensions.

### Category

```text
billing
bug
feature
other
```

### Urgency

```text
low
normal
high
```

A successful response follows a structured schema:

```json
{
  "category": "billing",
  "urgency": "high",
  "confidence": 0.94,
  "reason": "The customer reports a duplicate charge."
}
```

Pydantic models validate the model output before it is returned by the API.

---

## LLM Reliability

The triage service includes several safeguards around external model calls.

### Timeout Handling

Model requests use a configured request timeout to prevent indefinitely hanging requests.

### Selective Retries

Transient failures can be retried using exponential-style delays and jitter.

Retryable failures include:

```text
Timeout
Connection failure
HTTP 429
HTTP 5xx
```

Client errors such as `400`, `401`, and `403` are not blindly retried.

### Structured Output Validation

LLM responses are parsed and validated against the expected Pydantic schema.

The service also handles responses containing surrounding text or Markdown code fences by attempting to extract the JSON object.

### Repair Attempt

If the first model response does not satisfy the required schema, the service performs one repair attempt.

```text
LLM Response
     ↓
Parse JSON
     ↓
Pydantic Validation
     ↓
Invalid?
     │
     └── Yes → Repair Request
                    ↓
               Validate Again
```

If the repaired output is still invalid, information about the failure is written to a quarantine log for debugging.

---

## LLM Configuration

The model provider is configured through environment variables.

```env
LLM_BASE_URL=
LLM_API_KEY=
LLM_MODEL=
LLM_STUB=0
LLM_ENABLED=true
```

The implementation uses an OpenAI-compatible client interface, allowing compatible model providers to be configured without rewriting the triage service.

A local Ollama model was used during development and evaluation.

---

# 4. LLM Evaluation

The `evals/` directory contains a small evaluation harness for checking triage behavior against predefined scenarios.

```text
evals/
├── cases.json
└── run_eval.py
```

Cases include examples such as:

- Billing issues
- Application bugs
- Feature requests
- Refund requests
- Ambiguous requests
- Uncertain messages
- Prompt-injection attempts

The evaluation runner submits each case to the triage endpoint and compares the returned category with the expected category.

A recorded development evaluation produced:

```text
7 / 8 category matches
87.5%
```

This result represents the eight-case development evaluation set and should not be interpreted as general model accuracy.

The ambiguous-message case was the unsuccessful classification in that run.

---

# 5. LLM Observability

Model calls record operational metadata including:

```text
Timestamp
Prompt version
Model
Input tokens
Output tokens
Request duration
Whether repair was required
```

This provides basic visibility into model usage, latency, and structured-output reliability.

Prompt versions are stored separately under:

```text
prompts/
└── triage-v1.md
```

Separating prompts from application logic makes prompt changes easier to review and evaluate.

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
│   └── triage-v1.md
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