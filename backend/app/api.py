"""REST endpoints: authorization is enforced before lookup/serialization on every route."""
from datetime import date, datetime, time, timedelta
from urllib.parse import quote
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from fastapi.responses import Response
from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session, selectinload
from . import ai
from .config import settings
from .database import get_db
from .models import User, Book, Ticket, Message, AuditEvent, Attachment, utcnow
from .attachments import MAX_ATTACHMENT_BYTES, MAX_ATTACHMENTS, read_attachment
from .schemas import Login, TicketCreate, TicketUpdate, MessageCreate, DraftRequest, Category, Priority, Status
from .security import current_user, admin_user, verify_password, create_token, limiter, hash_password
from .serializers import user_view, book_view, ticket_view, attachment_view, iso

router = APIRouter(prefix='/api')
DUMMY_HASH = hash_password('timing-equalization-only')


def find_ticket(db, ticket_id, user):
    stmt = select(Ticket).where(Ticket.id == ticket_id)
    if user.role != 'admin':
        stmt = stmt.where(Ticket.author_id == user.id)
    ticket = db.scalar(stmt)
    if not ticket:
        raise HTTPException(404, 'Ticket not found.')
    return ticket


def check_version(ticket, version):
    if ticket.version != version:
        raise HTTPException(409, 'This ticket changed. Refresh it, review the latest content, and try again.')


def ticket_detail_view(db, ticket, user):
    result = ticket_view(ticket, admin=user.role == 'admin', detail=True)
    if user.role == 'admin':
        _, fingerprint = ai.draft_context(db, ticket)
        result['draft_stale'] = ticket.draft_context_hash != fingerprint
    return result


def audit(db, ticket, user, action):
    db.add(AuditEvent(ticket_id=ticket.id, actor=user.name, action=action))


@router.post('/auth/login', tags=['Authentication'])
def login(body: Login, request: Request, db: Session = Depends(get_db)):
    ip = request.client.host if request.client else 'unknown'
    limiter.check('login:' + ip, 20)
    user = db.scalar(select(User).where(User.email == body.email))
    valid = verify_password(body.password, user.password_hash if user else DUMMY_HASH)
    if not user or not valid:
        raise HTTPException(401, 'Email or password is incorrect.', headers={'WWW-Authenticate': 'Bearer'})
    return {'access_token': create_token(user), 'token_type': 'bearer',
            'expires_in': settings.token_expire_minutes * 60, 'user': user_view(user)}


@router.get('/auth/me', tags=['Authentication'])
def me(user: User = Depends(current_user)):
    return user_view(user)


@router.get('/meta', tags=['Reference'])
def metadata(user: User = Depends(current_user)):
    data = {'categories': [c.value for c in Category], 'priorities': [p.value for p in Priority],
            'statuses': [s.value for s in Status], 'poll_interval_seconds': 5,
            'attachment_max_bytes': MAX_ATTACHMENT_BYTES, 'attachment_limit': MAX_ATTACHMENTS}
    if user.role == 'admin':
        data.update({'ai_configured': bool(settings.openai_api_key.strip()), 'ai_model': settings.openai_model,
                     'knowledge_base_version': ai.KB['version']})
    return data


@router.get('/books', tags=['Books'])
def books(user: User = Depends(current_user), db: Session = Depends(get_db)):
    stmt = select(Book).order_by(Book.id)
    if user.role != 'admin':
        stmt = stmt.where(Book.author_id == user.id)
    return {'items': [book_view(book) for book in db.scalars(stmt)]}


@router.get('/books/{book_id}', tags=['Books'])
def book_detail(book_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    stmt = select(Book).where(Book.id == book_id)
    if user.role != 'admin':
        stmt = stmt.where(Book.author_id == user.id)
    book = db.scalar(stmt)
    if not book:
        raise HTTPException(404, 'Book not found.')
    return book_view(book)


def ticket_list(db, user, status=None, category=None, priority=None, date_from=None, date_to=None,
                q=None, assignment=None, page=1, page_size=20):
    if date_from and date_to and date_from > date_to:
        raise HTTPException(422, 'Start date must not be after end date.')
    stmt = select(Ticket)
    if user.role != 'admin':
        stmt = stmt.where(Ticket.author_id == user.id)
    for column, value in [(Ticket.status, status), (Ticket.category, category), (Ticket.priority, priority)]:
        if value:
            stmt = stmt.where(column == value.value)
    if date_from:
        stmt = stmt.where(Ticket.created_at >= datetime.combine(date_from, time.min))
    if date_to:
        stmt = stmt.where(Ticket.created_at <= datetime.combine(date_to, time.max))
    if q:
        stmt = stmt.where(or_(Ticket.subject.icontains(q, autoescape=True), Ticket.description.icontains(q, autoescape=True),
                              Ticket.author.has(User.name.icontains(q, autoescape=True)),
                              Ticket.book.has(Book.title.icontains(q, autoescape=True))))
    if assignment == 'mine':
        stmt = stmt.where(Ticket.assigned_to == user.id)
    elif assignment == 'unassigned':
        stmt = stmt.where(Ticket.assigned_to.is_(None))
    elif assignment not in (None, 'all'):
        raise HTTPException(422, 'Assignment must be mine, unassigned or all.')
    count = db.scalar(select(func.count()).select_from(stmt.subquery()))
    # Unresolved first; highest priority first; oldest first within each priority.
    order = [case((Ticket.status.in_(['Open', 'In Progress']), 0), else_=1),
             case((Ticket.priority == 'Critical', 0), (Ticket.priority == 'High', 1),
                  (Ticket.priority == 'Medium', 2), else_=3), Ticket.created_at.asc(), Ticket.id]
    stmt = stmt.options(selectinload(Ticket.author), selectinload(Ticket.book), selectinload(Ticket.assignee))
    items = db.scalars(stmt.order_by(*order).offset((page - 1) * page_size).limit(page_size)).all()
    return {'items': [ticket_view(t, admin=user.role == 'admin') for t in items], 'total': count, 'page': page, 'page_size': page_size}


@router.get('/tickets', tags=['Author tickets'])
def author_tickets(status: Status | None = None, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                   user: User = Depends(current_user), db: Session = Depends(get_db)):
    return ticket_list(db, user, status=status, page=page, page_size=page_size)


@router.post('/tickets', status_code=201, tags=['Author tickets'])
def create_ticket(body: TicketCreate, tasks: BackgroundTasks, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if user.role != 'author':
        raise HTTPException(403, 'Use an author account to submit a ticket.')
    limiter.check('create-ticket:' + user.id, 12)
    if body.book_id and not db.scalar(select(Book.id).where(Book.id == body.book_id, Book.author_id == user.id)):
        raise HTTPException(404, 'Book not found in your account.')
    ticket = Ticket(author_id=user.id, **body.model_dump())
    db.add(ticket)
    db.flush()
    audit(db, ticket, user, 'Ticket created.')
    db.commit()  # The ticket is durable BEFORE any LLM work is scheduled.
    result = ticket_view(ticket, detail=True)
    tasks.add_task(ai.apply_triage, ticket.id)
    return result


@router.get('/tickets/{ticket_id}', tags=['Author tickets'])
def ticket_detail(ticket_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return ticket_detail_view(db, find_ticket(db, ticket_id, user), user)


@router.post('/tickets/{ticket_id}/attachments', status_code=201, tags=['Attachments'],
             openapi_extra={'requestBody': {'required': True, 'content': {
                 kind: {'schema': {'type': 'string', 'format': 'binary'}}
                 for kind in ('image/png', 'image/jpeg', 'application/pdf')}}})
async def upload_attachment(ticket_id: str, request: Request, filename: str = Query(min_length=1, max_length=250),
                            user: User = Depends(current_user), db: Session = Depends(get_db)):
    find_ticket(db, ticket_id, user)  # Authorize before reading file bytes.
    limiter.check('upload:' + user.id, 12)
    db.rollback()  # Do not hold a transaction open while the client uploads.
    filename, content_type, content = await read_attachment(request, filename)
    ticket = find_ticket(db, ticket_id, user)
    if ticket.status == 'Closed':
        raise HTTPException(409, 'Reopen the ticket before adding an attachment.')
    count = db.scalar(select(func.count()).select_from(Attachment).where(Attachment.ticket_id == ticket.id))
    if count >= MAX_ATTACHMENTS:
        raise HTTPException(409, f'A ticket can contain at most {MAX_ATTACHMENTS} attachments.')
    attachment = Attachment(ticket_id=ticket.id, uploaded_by=user.id, filename=filename,
                            content_type=content_type, size_bytes=len(content), content=content)
    db.add(attachment)
    # Increment the ticket version so simultaneous uploads cannot exceed the limit,
    # and concurrent edits/drafts detect the changed supporting evidence.
    ticket.updated_at = utcnow()
    audit(db, ticket, user, 'Supporting attachment uploaded.')
    db.commit()
    return attachment_view(attachment)


@router.get('/tickets/{ticket_id}/attachments/{attachment_id}', tags=['Attachments'],
            responses={200: {'description': 'Authenticated file download', 'content': {
                'application/octet-stream': {'schema': {'type': 'string', 'format': 'binary'}}}}})
def download_attachment(ticket_id: str, attachment_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    find_ticket(db, ticket_id, user)
    attachment = db.scalar(select(Attachment).where(Attachment.id == attachment_id, Attachment.ticket_id == ticket_id))
    if not attachment:
        raise HTTPException(404, 'Attachment not found.')
    return Response(attachment.content, media_type=attachment.content_type,
                    headers={'Content-Disposition': "attachment; filename*=UTF-8''" + quote(attachment.filename, safe=''),
                             'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff'})


def append_message(db, ticket, body, user):
    check_version(ticket, body.version)
    if user.role != 'admin' and (body.kind != 'reply' or body.resolve):
        raise HTTPException(403, 'Authors cannot add internal notes or resolve tickets.')
    if ticket.status == 'Closed':
        raise HTTPException(409, 'This ticket is closed. An admin can reopen it, or the author can create a new ticket.')
    db.add(Message(ticket_id=ticket.id, sender_id=user.id, kind=body.kind, body=body.body))
    if body.kind == 'reply':
        if user.role == 'author' and ticket.status == 'Resolved':
            ticket.status = 'Open'
        elif user.role == 'admin' and ticket.status == 'Open':
            ticket.status = 'In Progress'
        if user.role == 'admin' and body.resolve:
            ticket.status = 'Resolved'
    elif body.resolve:
        raise HTTPException(422, 'An internal note cannot be sent as a resolution reply.')
    ticket.updated_at = utcnow()
    audit(db, ticket, user, 'Internal note added.' if body.kind == 'note' else 'Reply sent' + (' and ticket resolved.' if body.resolve else '.'))
    db.commit()
    db.expire(ticket, ['messages', 'events'])
    return ticket_detail_view(db, ticket, user)


@router.post('/tickets/{ticket_id}/messages', status_code=201, tags=['Author tickets'])
def author_message(ticket_id: str, body: MessageCreate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return append_message(db, find_ticket(db, ticket_id, user), body, user)


@router.get('/admin/overview', tags=['Administration'])
def overview(user: User = Depends(admin_user), db: Session = Depends(get_db)):
    counts = {s.value: 0 for s in Status}
    counts.update(dict(db.execute(select(Ticket.status, func.count()).group_by(Ticket.status)).all()))
    unresolved = [Ticket.status.in_(['Open', 'In Progress'])]
    urgent = db.scalar(select(func.count()).select_from(Ticket).where(*unresolved, Ticket.priority.in_(['Critical', 'High'])))
    aging = db.scalar(select(func.count()).select_from(Ticket).where(*unresolved, Ticket.created_at < utcnow() - timedelta(hours=48)))
    return {'counts': counts, 'urgent': urgent, 'waiting_over_48h': aging, 'total': sum(counts.values())}


@router.get('/admin/tickets', tags=['Administration'])
def admin_tickets(status: Status | None = None, category: Category | None = None, priority: Priority | None = None,
                  date_from: date | None = None, date_to: date | None = None, q: str | None = Query(None, max_length=150),
                  assignment: str | None = None, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                  user: User = Depends(admin_user), db: Session = Depends(get_db)):
    return ticket_list(db, user, status, category, priority, date_from, date_to, q, assignment, page, page_size)


@router.get('/admin/tickets/{ticket_id}', tags=['Administration'])
def admin_detail(ticket_id: str, user: User = Depends(admin_user), db: Session = Depends(get_db)):
    ticket = find_ticket(db, ticket_id, user)
    return ticket_detail_view(db, ticket, user)


@router.patch('/admin/tickets/{ticket_id}', tags=['Administration'])
def update_ticket(ticket_id: str, body: TicketUpdate, user: User = Depends(admin_user), db: Session = Depends(get_db)):
    ticket = find_ticket(db, ticket_id, user)
    check_version(ticket, body.version)
    changes = []
    for key in ['status', 'category', 'priority']:
        value = getattr(body, key)
        if value is not None:
            changes.append(f'{key}: {getattr(ticket, key)} -> {value.value}')
            setattr(ticket, key, value.value)
            if key in ('category', 'priority'):
                setattr(ticket, key + '_overridden', True)
    if body.assignment:
        ticket.assigned_to = user.id if body.assignment == 'self' else None
        changes.append('Assigned to ' + user.name if body.assignment == 'self' else 'Unassigned')
    if not changes:
        raise HTTPException(422, 'Provide at least one change.')
    ticket.updated_at = utcnow()
    audit(db, ticket, user, '; '.join(changes))
    db.commit()
    db.expire(ticket, ['events', 'assignee'])
    return ticket_detail_view(db, ticket, user)


@router.post('/admin/tickets/{ticket_id}/messages', status_code=201, tags=['Administration'])
def admin_message(ticket_id: str, body: MessageCreate, user: User = Depends(admin_user), db: Session = Depends(get_db)):
    return append_message(db, find_ticket(db, ticket_id, user), body, user)


@router.post('/admin/tickets/{ticket_id}/triage', status_code=202, tags=['AI assistance'])
def retry_triage(ticket_id: str, tasks: BackgroundTasks, user: User = Depends(admin_user), db: Session = Depends(get_db)):
    limiter.check('ai:' + user.id, 10)
    ticket = find_ticket(db, ticket_id, user)
    if ticket.triage_status == 'pending':
        raise HTTPException(409, 'Triage is already running.')
    ticket.triage_status = 'pending'
    db.commit()
    tasks.add_task(ai.apply_triage, ticket.id)
    return {'status': 'pending', 'message': 'Triage scheduled; human overrides are preserved.'}


def draft_view(ticket, cached):
    return {'text': ticket.draft_text, 'source': ticket.draft_source, 'review_notes': ticket.draft_review_notes,
            'generated_at': iso(ticket.draft_generated_at), 'cached': cached, 'version': ticket.version}


@router.post('/admin/tickets/{ticket_id}/draft', tags=['AI assistance'])
def draft(ticket_id: str, body: DraftRequest, user: User = Depends(admin_user), db: Session = Depends(get_db)):
    ticket = find_ticket(db, ticket_id, user)
    context, fingerprint = ai.draft_context(db, ticket)
    if ticket.draft_text and ticket.draft_context_hash == fingerprint and not body.force:
        return draft_view(ticket, True)
    limiter.check('ai:' + user.id, 10)
    # Release the read transaction before network I/O. Recheck context after it returns.
    db.rollback()
    outcome = ai.generate_draft(context)
    ticket = find_ticket(db, ticket_id, user)
    _, current_fingerprint = ai.draft_context(db, ticket)
    if fingerprint != current_fingerprint:
        raise HTTPException(409, 'The conversation changed while drafting. Please generate a fresh draft.')
    ticket.draft_text = outcome.result.reply
    ticket.draft_review_notes = outcome.result.review_notes
    ticket.draft_context_hash = fingerprint
    ticket.draft_source = outcome.source
    ticket.draft_generated_at = utcnow()
    ticket.ai_input_tokens += outcome.input_tokens
    ticket.ai_output_tokens += outcome.output_tokens
    audit(db, ticket, user, f'Prepared {outcome.source} draft for review. No reply sent.')
    db.commit()
    return draft_view(ticket, False)
