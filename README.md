# AuthorCare Author Support & Communication Portal

A support portal where authors can view their books, check royalty information, and raise queries. The operations team can manage tickets, review AI-generated responses, and communicate with authors from a shared dashboard.

Built with React, FastAPI, SQLAlchemy, and OpenAI. Supports PostgreSQL and SQLite.

## Features

### Author portal

- Email and password login.
- Access restricted to the signed-in author's books and tickets.
- Book details, production status, sales, and royalty information.
- Book-specific and general support queries.
- PNG, JPG, and PDF attachments: up to three files per ticket, with a maximum size of 5 MiB each.
- Ticket history, status updates, and public replies.
- Automatic updates through five-second polling while the page is visible.

### Admin portal

- Ticket queue with status, category, priority, date, assignment, and search filters.
- Unresolved tickets ordered by priority and age.
- Automatic AI classification and priority assignment, with manual overrides.
- Editable response drafts based on the supplied AuthorCare policies and relevant account information.
- Public replies, private internal notes, status changes, and self-assignment.
- Authenticated attachment downloads and ticket activity history.
- Version checks to prevent conflicting updates from silently overwriting each other.

## Technology

| Component | Technology |
| --- | --- |
| Frontend | React and Vite |
| Backend | Python and FastAPI |
| Database access | SQLAlchemy |
| Database | PostgreSQL or SQLite |
| Authentication | Signed JWTs and scrypt password hashes |
| AI integration | OpenAI, with `gpt-4o-mini` as the default model |
| Testing | pytest |
| Deployment | Docker |
| CI | GitHub Actions |

## Local setup on Windows

### Prerequisites

- Python 3.12 with the Windows Python launcher.
- Node.js 22 or newer.
- PostgreSQL if using a PostgreSQL connection.
- An OpenAI API key for live classification and response generation.

SQLite is available for local evaluation without a separate database server.

### 1. Configure the environment

Open PowerShell in the project root, then run:

```powershell
if (-not (Test-Path .env)) {
    Copy-Item .env.example .env
}
notepad .env
```

Set the following values in `.env`:

```dotenv
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4o-mini
AUTO_SEED=true
```

For PostgreSQL, create the database and database user first, then set:

```dotenv
DATABASE_URL=postgresql+psycopg://DATABASE_USER:URL_ENCODED_PASSWORD@127.0.0.1:5432/DATABASE_NAME
```

Replace the placeholders with your local connection details. URL-encode special characters in the password.

For SQLite, leave the value empty:

```dotenv
DATABASE_URL=
```

The SQLite database is created at `backend/data/authorcare.db`.

Keep `.env` out of version control. Restart the backend after changing environment variables.

### 2. Install dependencies and build

```powershell
powershell -ExecutionPolicy Bypass -File .\setup.ps1
```

The setup script creates the virtual environment, installs dependencies, builds the frontend, and seeds the supplied 10 authors and 18 books.

Seeding is idempotent: existing accounts and records are preserved.

### 3. Start the application

```powershell
powershell -ExecutionPolicy Bypass -File .\run.ps1
```

| Service | Local URL |
| --- | --- |
| Application | http://127.0.0.1:8000 |
| Interactive API documentation | http://127.0.0.1:8000/docs |
| Health check | http://127.0.0.1:8000/health |

The backend serves the compiled frontend and API from the same port.

If the AI key is missing or the provider request fails, tickets and manual replies remain available. Classification and drafts use clearly labelled fallbacks.

## Demo accounts

These credentials are for the supplied sample dataset only.

| Account | Email | Password |
| --- | --- | --- |
| Admin | admin@authorcare.demo | AdminDemo!2026 |
| Priya Sharma | priya.sharma@email.com | AuthorDemo!2026 |
| Rohit Kapoor | rohit.kapoor@email.com | AuthorDemo!2026 |
| Ananya Reddy | ananya.reddy@email.com | AuthorDemo!2026 |
| Vikram Joshi | vikram.joshi@email.com | AuthorDemo!2026 |
| Meera Nair | meera.nair@email.com | AuthorDemo!2026 |
| Arjun Malhotra | arjun.malhotra@email.com | AuthorDemo!2026 |
| Sneha Kulkarni | sneha.kulkarni@email.com | AuthorDemo!2026 |
| Farhan Sheikh | farhan.sheikh@email.com | AuthorDemo!2026 |
| Kavita Deshmukh | kavita.deshmukh@email.com | AuthorDemo!2026 |
| Diya Chatterjee | diya.chatterjee@email.com | AuthorDemo!2026 |

Use separate browser sessions to test the author and admin interfaces together.

Account environment variables apply when accounts are first created. Changing those variables later does not reset existing passwords.

## Development mode

Run these commands in separate PowerShell terminals from the project root.

Backend:

```powershell
powershell -ExecutionPolicy Bypass -File .\dev-backend.ps1
```

Frontend:

```powershell
powershell -ExecutionPolicy Bypass -File .\dev-frontend.ps1
```

Open http://127.0.0.1:5173. Vite forwards API requests to the backend on port 8000.

When using `run.ps1`, rebuild the frontend after changing React files:

```powershell
Push-Location frontend
npm.cmd run build
Pop-Location
```

## Architecture

FastAPI serves the REST API and compiled React frontend. Keeping both in one service simplifies deployment and avoids separate frontend/backend origins.

The backend separates routes, validation, database models, authentication, serialization, and AI integration. SQLAlchemy provides database access for both PostgreSQL and SQLite. Monetary values use fixed-precision numeric columns.

| Location | Responsibility |
| --- | --- |
| `backend/app/main.py` | Application startup, error handling, health checks, and frontend serving |
| `backend/app/api.py` | Endpoints, permissions, ticket workflow, filtering, and version checks |
| `backend/app/models.py` | Users, books, tickets, messages, attachments, and audit events |
| `backend/app/schemas.py` | Request validation and AI output schemas |
| `backend/app/security.py` | Password hashing, authentication, and rate limiting |
| `backend/app/serializers.py` | Role-specific response fields |
| `backend/app/ai.py` | Prompts, provider requests, fallbacks, and draft caching |
| `backend/app/attachments.py` | Upload limits and file validation |
| `backend/app/seed.py` | Sample-data import |
| `backend/app/verify_ai.py` | Live provider verification |
| `backend/data/` | Supplied sample data and structured knowledge base |
| `backend/tests/` | API, permissions, attachment, and AI integration tests |
| `frontend/src/pages/` | Author and admin screens |
| `frontend/src/components/` | Shared interface components |
| `frontend/src/api.js` | API requests, authentication headers, and polling |
| `docs/` | API, implementation approach, and deployment documentation |

## AI integration

The default model is `gpt-4o-mini`. It was selected for the bounded classification and drafting tasks, with structured outputs and controlled token usage. The model is configurable through `OPENAI_MODEL`.

### Classification and priority

The application saves a ticket before scheduling the AI request. One request produces both its category and priority.

The response is validated before being stored. Manual category and priority overrides remain authoritative when classification is retried.

### Response drafting

Drafts use relevant knowledge-base sections, book details, the author's accumulated pending royalty balance, and a bounded selection of recent public messages.

Private notes and unrelated authors' records are excluded. Attachment filenames and types can be included, but file contents are not sent to the model.

Prompts instruct the model to avoid inventing payment dates, bank verification, production estimates, or completed operational actions. The model has no tools for making payments, arranging reprints, or changing marketplace listings.

An admin reviews and edits the draft before sending it. Generating a draft does not publish a reply.

### Reliability and cost controls

- JSON-schema responses with Pydantic validation.
- Request timeouts and explicit handling of provider errors.
- Labelled rule-based classification and template drafts when AI is unavailable.
- Combined category and priority generation.
- Relevant policy sections and bounded conversation context.
- Output limits of 400 tokens for triage and 1,100 tokens for drafts.
- No automatic retries of provider calls.
- Reuse of drafts when their context has not changed.
- Cache invalidation when relevant conversation, classification, attachment metadata, or AI configuration changes.

## Data assumptions

The supplied dataset is imported without changing its IDs, dates, null values, or royalty figures.

- Royalty threshold handling uses the author's accumulated pending balance across books.
- The data does not contain bank verification, quarterly transaction ledgers, printing-cost breakdowns, or platform-level sales.
- Publication channels are recorded values, not a live stock feed.
- A production stage does not establish the cause of a delay or a completion date.
- Placeholder ISBN values are retained from the supplied dataset.
- The application manages support conversations; it does not execute payments, send emails, arrange reprints, or update external marketplaces.

## Testing

Run the backend tests from the project root:

```powershell
Push-Location backend
..\.venv\Scripts\python.exe -m pytest
Pop-Location
```

By default, tests use an isolated SQLite database and mocked provider responses. They do not use the application's PostgreSQL database or make billable AI requests.

The suite covers authentication, ownership checks, ticket workflows, private-note visibility, filters, concurrency, attachment validation, and AI success/failure handling.

Check the frontend build:

```powershell
Push-Location frontend
npm.cmd run build
Pop-Location
```

Run the live OpenAI check separately:

```powershell
powershell -ExecutionPolicy Bypass -File .\verify-ai.ps1
```

This makes two billable provider requests using the configured API key. Both classification and drafting should report `llm` as their source.

The GitHub Actions workflow is configured to run backend tests against SQLite and PostgreSQL, along with a frontend production build. Workflow results are available in the repository's Actions tab after it runs.

## Documentation

- [API guide](docs/API.md)
- [Implementation approach](docs/APPROACH.md)
- [Deployment guide](docs/DEPLOYMENT.md)

## Limitations and future improvements

- Updates use five-second polling rather than WebSockets.
- Background tasks and rate limits run within one application process. Multiple workers would require a durable queue and shared rate limiting.
- Login tokens expire, but logout does not revoke an already-issued token.
- Demo accounts use shared passwords. Registration, password recovery, and MFA are not implemented.
- Attachments are stored in the database. File scanning, retention rules, and object storage would be needed for production use.
- Database tables are created automatically; versioned schema migrations are not included.
- Automated browser interaction tests are not included.
- AI responses still require human review. Prompt constraints cannot guarantee factual accuracy.
- Concurrent draft requests are checked for stale context but may still incur separate provider charges.

Production work would also include monitoring, backups, stronger session management, and evaluation of AI response quality against a maintained test set.