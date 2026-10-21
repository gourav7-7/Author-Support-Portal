# Implementation approach

The main priority was a complete support workflow: authors can see their books, raise queries, and receive replies; administrators can review tickets, manage their status, and respond with relevant account information.

## Architecture

React handles the author and admin interfaces. FastAPI provides the REST API, authentication, and server-side access checks. SQLAlchemy stores the application data and supports PostgreSQL alongside SQLite for simple local evaluation. The Docker image serves the frontend and API together, keeping deployment to one application service.

The supplied dataset is imported without changing its records. Authors can access only their own books, tickets, and attachments. Internal notes are filtered out of author responses. Ticket updates include a record version so simultaneous edits return a conflict instead of silently overwriting newer changes.

## AI integration

Tickets are saved before classification begins, so a provider failure does not prevent submission. A single structured-output request produces the category and priority. Administrators can override either field, and those choices are preserved on retries.

Response drafts combine relevant BookLeaf policies, book details, accumulated pending royalties, and recent public messages. Private notes and unrelated account data are excluded. Attachment contents are not sent to the model.

The model cannot perform operational actions. Prompts instruct it to avoid inventing payment dates, verification results, or completed actions. An administrator reviews and edits each response before sending it.

Cost controls include bounded context, output limits, combined classification, draft caching, and explicit rather than automatic retries. Provider failures produce labelled fallbacks while manual replies remain available.

## Trade-offs and next steps

Five-second polling provides near-real-time updates with a small implementation. In-process background tasks and rate limits suit a single-service demo but would need shared infrastructure for multiple workers.

Attachments use authenticated downloads and bounded database storage. A production version would move files to object storage and add scanning and retention rules.

The sample data does not include transaction ledgers, bank verification, or production delay reasons. Responses therefore acknowledge those gaps instead of supplying unsupported details.

Further work would add durable task processing, database migrations, revocable sessions, monitoring, automated browser tests, and a maintained evaluation set for AI response quality.