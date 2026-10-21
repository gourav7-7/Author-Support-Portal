# API guide

Interactive OpenAPI documentation is served at `/docs`; the schema is at `/openapi.json`. Use `POST /api/auth/login` with JSON email/password, copy `access_token`, and use the Authorize button in Swagger. Application routes require `Authorization: Bearer <token>`; login, documentation and `/health` are public.

## Endpoints

| Method | Path | Role | Purpose |
| --- | --- | --- | --- |
| POST | `/api/auth/login` | Public | JSON email/password to expiring access token |
| GET | `/api/auth/me` | Signed in | Current user's safe profile |
| GET | `/api/meta` | Signed in | Categories, priorities, statuses; admin-only AI configuration indicator |
| GET | `/api/books` | Signed in | Own books for authors, all books for admins |
| GET | `/api/books/{id}` | Signed in | Own book or admin-accessible book |
| GET | `/api/tickets` | Signed in | Own tickets for authors, all for admins; status filter and pagination |
| POST | `/api/tickets` | Author | Save book-specific or general ticket and schedule triage |
| GET | `/api/tickets/{id}` | Owner/admin | Ticket and permitted messages; private fields excluded for authors |
| POST | `/api/tickets/{id}/messages` | Owner/admin | Public follow-up; only admins may add notes or resolve |
| POST | `/api/tickets/{id}/attachments?filename=...` | Owner/admin | Raw PNG/JPEG/PDF body, up to 5 MiB, maximum 3 files/ticket |
| GET | `/api/tickets/{id}/attachments/{attachment_id}` | Owner/admin | Authenticated download with attachment disposition |
| GET | `/api/admin/overview` | Admin | Status counts, urgent unresolved and unresolved older than 48h |
| GET | `/api/admin/tickets` | Admin | Full filtered queue |
| GET | `/api/admin/tickets/{id}` | Admin | Ticket, draft state, notes and audit events |
| PATCH | `/api/admin/tickets/{id}` | Admin | Status/category/priority and self-assignment changes |
| POST | `/api/admin/tickets/{id}/messages` | Admin | Reply or private note; optional send-and-resolve |
| POST | `/api/admin/tickets/{id}/triage` | Admin | Retry model classification; retain human overrides |
| POST | `/api/admin/tickets/{id}/draft` | Admin | Get/reuse a context-grounded draft; `{ "force": true }` regenerates |
| GET | `/health` | Public | Database connectivity and process health |

## Examples

Login:

```json
{"email":"priya.sharma@email.com","password":"AuthorDemo!2026"}
```

Create a ticket. Omit `book_id` or set it to null for General / Account Level:

```json
{"book_id":"BK001","subject":"Pending royalty question","description":"Please help me understand the royalty period covered by my pending balance."}
```

Update a ticket using the **current version returned by GET**, not a hardcoded value:

```json
{"version":3,"status":"In Progress","category":"Royalty & Payments","priority":"High","assignment":"self"}
```

Send a public reply and resolve:

```json
{"version":4,"body":"Your reviewed response here.","kind":"reply","resolve":true}
```

Save an internal note:

```json
{"version":5,"body":"Operations-only context here.","kind":"note"}
```

Get a cached/current draft: `POST` with `{}`. A draft response contains `text`, `source` (`llm` or `fallback`), `review_notes`, `generated_at`, `cached` and the current ticket `version`. No public message is sent.

## Queue filters and pagination

`status`, `category`, `priority`, `date_from`, `date_to`, `q`, `assignment`, `page`, `page_size`.

- Dates are inclusive UTC creation dates in `YYYY-MM-DD` format. UI timestamps use the viewer's locale/timezone.
- `assignment`: `all`, `mine` or `unassigned`.
- `q` searches subject, description, author name and book title case-insensitively on SQLite and PostgreSQL.
- Page starts at 1; page size is 1-100. Response shape: `{ "items": [...], "total": 18, "page": 1, "page_size": 20 }`.
- Queue order: unresolved first, then Critical/High/Medium/Low, then oldest creation time. Waiting over 48 hours is an operational highlight, not an asserted universal SLA breach.

## Workflow and errors

Authors can reply to their own Open/In Progress/Resolved tickets; a reply to a Resolved ticket reopens it. Closed tickets reject new replies until an admin reopens them. Admins can explicitly move between the four statuses. A first admin reply moves Open to In Progress unless send-and-resolve is selected. Notes never resolve a ticket. Assigned admin does not restrict other admins from accessing the queue.

Errors use `{ "error": { "code": "...", "message": "...", "details": [...] } }`; details are included for validation only. Common statuses: 401 sign-in required, 403 forbidden role, 404 missing/unowned object, 409 version/workflow conflict, 422 invalid fields, 429 rate limit, 503 database unavailable. An unowned ID returns 404 to avoid exposing another author's record existence. Unexpected faults return a sanitized 500; validation failures have specific messages.

The admin activity history records actions without sending its contents to authors or the model. Auto triage changes and draft generation also advance the ticket version. On a 409, read the current ticket, review any changes and retry; never blindly overwrite with a stale version.

## Supporting files

Upload **raw file bytes**, not JSON/base64 or multipart, in a separate request after the ticket is created. Pass a URL-encoded filename as the `filename` query parameter and the file's `Content-Type` (`image/png`, `image/jpeg`, or `application/pdf`). The server verifies the filename extension and initial file signature; the client-provided MIME type does not override validation. Empty files return 422, unsupported/mismatched files 415, files above 5 MiB 413, and closed tickets or a fourth file 409. Unknown/unowned tickets and attachments return 404. All requests need the bearer token.

The 201 response contains attachment metadata only: `id`, `filename`, `content_type`, `size_bytes` and `created_at`. Ticket-detail responses include an `attachments` array with the same fields. Download through the authenticated GET endpoint; never expose database bytes in the ticket JSON. Supporting files are visible to the author and all admins; internal-note attachments are not supported. Adding a file advances the ticket version and invalidates an existing draft. The model receives filename/type metadata only and cannot inspect the file contents.
