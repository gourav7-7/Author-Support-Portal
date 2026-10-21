# Deployment

The application runs as one web service backed by a persistent database. The Dockerfile builds the React frontend and serves it through FastAPI.

## Local Docker setup

Start Docker and run the following commands from the project root.

Create `.env` only if it does not already exist:

```powershell
if (-not (Test-Path .env)) {
    Copy-Item .env.example .env
}
```

Set `OPENAI_API_KEY` in `.env` to enable live AI features.

### PostgreSQL

Add a password for the container's database to `.env`:

```dotenv
POSTGRES_PASSWORD=your_url_safe_database_password
```

Use a URL-safe password because the Compose configuration includes it in the database connection URI.

Start the application and database:

```powershell
docker compose -f compose.yml -f compose.postgres.yml up --build
```

This creates a separate PostgreSQL database inside Docker. It does not connect to or migrate records from a PostgreSQL installation on the host.

The PostgreSQL override supplies the application's container database URL, so the native Windows connection URL in `.env` is not used by this configuration.

Open:

- Application: http://127.0.0.1:8000
- API documentation: http://127.0.0.1:8000/docs
- Health check: http://127.0.0.1:8000/health

Stop the services:

```powershell
docker compose -f compose.yml -f compose.postgres.yml down
```

Database records persist in a named Docker volume. Adding `-v` to the shutdown command deletes the volumes and their data.

### SQLite alternative

The base Compose configuration also supports SQLite.

With `DATABASE_URL` empty in `.env` and no shell-level override, it uses a database under `/app/runtime`, backed by a named volume:

```powershell
docker compose up --build
```

A nonempty `DATABASE_URL` overrides this default. A host address such as `127.0.0.1` refers to the container itself when used inside Docker.

## Hosted deployment

Use a hosting environment that can build the root Dockerfile, run a persistent web service, and connect to PostgreSQL.

1. Connect the source repository.
2. Set the build context to the repository root and use `Dockerfile`.
3. Provision a PostgreSQL database accessible to the application.
4. Add the runtime environment variables listed below.
5. Configure `/health` as the health-check endpoint.
6. Deploy the service and enable HTTPS.

The image starts Uvicorn on `0.0.0.0` and uses the `PORT` environment variable, defaulting to port 8000.

Run one application worker with the current implementation. Background processing and rate limits are process-local.

## Environment variables

Configure secrets through the hosting platform's environment settings.

| Variable | Configuration |
| --- | --- |
| `APP_ENV` | `production` |
| `DATABASE_URL` | PostgreSQL connection URL |
| `JWT_SECRET` | A random secret of at least 32 characters |
| `OPENAI_API_KEY` | OpenAI API key |
| `OPENAI_MODEL` | `gpt-4o-mini` |
| `AUTO_SEED` | `true` to initialize the supplied dataset |
| `ADMIN_EMAIL` | `admin@authorcare.demo`, or the documented demo admin email |
| `DEMO_AUTHOR_PASSWORD` | Password for author accounts created during initial seeding |
| `DEMO_ADMIN_PASSWORD` | Password for the admin account created during initial seeding |
| `PORT` | Hosting-provided port, or `8000` |

Generate a JWT secret locally:

```powershell
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(48))"
```

Store the generated value in the hosting environment.

The Docker image sets `FRONTEND_DIST` automatically. The same application serves the frontend and API, so a separate frontend deployment is not required.

## Initial data and accounts

With `AUTO_SEED=true`, startup creates missing tables and imports the supplied authors and books.

Seeding preserves existing records. Password environment variables affect newly created accounts only; changing them does not reset passwords for accounts already in the database.

Keep the demo credentials in the README consistent with the deployed accounts. Use the supplied sample data rather than real customer information.

## Deployment checks

After deployment:

1. Open `/health` and confirm a successful response.
2. Sign in as an author and confirm that only that author's records are visible.
3. Create a ticket and upload a supported attachment.
4. Sign in as an admin in a separate browser session.
5. Confirm that AI classification and drafting report `llm` rather than fallback.
6. Edit and send a response, then confirm it appears in the author session.
7. Save an internal note and verify that it remains hidden from the author.
8. Check status changes, assignment, and queue filters.
9. Restart the service and confirm that tickets and attachments remain available.

Record the working application URL in the README.

## Persistence and security

PostgreSQL stores the application records and uploaded attachment bytes. Configure database backups through the hosting environment.

If deploying with SQLite instead, mount persistent storage at `/app/runtime` and set:

```dotenv
DATABASE_URL=sqlite:////app/runtime/authorcare.db
```

A database stored only on an ephemeral container filesystem can be lost during replacement or redeployment.

Keep `.env`, API keys, database passwords, JWT secrets, database exports, and private uploads out of the repository.

Shared demo admin access can generate billable AI requests. Monitor API usage and configure the provider's available spending controls for the evaluation period.