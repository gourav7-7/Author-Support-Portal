from .models import Attachment, Book, Ticket, User


def iso(value):
    return value.isoformat() + 'Z' if value else None


def user_view(user: User):
    return {'id': user.id, 'name': user.name, 'email': user.email, 'role': user.role, 'city': user.city}


def book_view(book: Book):
    # Explicit fields prevent accidental exposure as the schema grows.
    result = {'book_id': book.id, 'author_id': book.author_id, 'title': book.title, 'isbn': book.isbn,
              'genre': book.genre, 'status': book.status, 'total_copies_sold': book.total_copies_sold,
              'print_partner': book.print_partner, 'available_on': book.available_on}
    for key in ['mrp', 'author_royalty_per_copy', 'total_royalty_earned', 'royalty_paid', 'royalty_pending']:
        value = getattr(book, key)
        result[key] = float(value) if value is not None else None
    for key in ['publication_date', 'last_royalty_payout_date']:
        value = getattr(book, key)
        result[key] = value.isoformat() if value else None
    return result


def attachment_view(attachment: Attachment):
    return {'id': attachment.id, 'filename': attachment.filename,
            'content_type': attachment.content_type, 'size_bytes': attachment.size_bytes,
            'created_at': iso(attachment.created_at)}


def ticket_view(ticket: Ticket, admin=False, detail=False):
    data = {'id': ticket.id, 'reference': 'BL-' + ticket.id[:8].upper(), 'subject': ticket.subject,
            'description': ticket.description, 'book_id': ticket.book_id,
            'book_title': ticket.book.title if ticket.book else None, 'status': ticket.status,
            'category': ticket.category, 'priority': ticket.priority, 'created_at': iso(ticket.created_at),
            'updated_at': iso(ticket.updated_at), 'version': ticket.version}
    if detail:
        data['book'] = book_view(ticket.book) if ticket.book else None
        data['attachments'] = [attachment_view(a) for a in ticket.attachments]
        data['messages'] = [{'id': m.id, 'body': m.body, 'kind': m.kind, 'sender_name': m.sender.name,
                             'sender_role': m.sender.role, 'created_at': iso(m.created_at)}
                            for m in ticket.messages if admin or m.kind == 'reply']
    if admin:
        data.update({'author': user_view(ticket.author), 'assigned_to': ticket.assigned_to,
                     'assignee_name': ticket.assignee.name if ticket.assignee else None,
                     'triage_status': ticket.triage_status, 'triage_source': ticket.triage_source,
                     'triage_reason': ticket.triage_reason, 'ai_category': ticket.ai_category,
                     'ai_priority': ticket.ai_priority, 'ai_error': ticket.ai_error,
                     'category_overridden': ticket.category_overridden, 'priority_overridden': ticket.priority_overridden})
        if detail:
            data.update({'draft_text': ticket.draft_text, 'draft_source': ticket.draft_source,
                         'draft_generated_at': iso(ticket.draft_generated_at),
                         'draft_review_notes': ticket.draft_review_notes,
                         'ai_input_tokens': ticket.ai_input_tokens, 'ai_output_tokens': ticket.ai_output_tokens,
                         'events': [{'actor': e.actor, 'action': e.action, 'created_at': iso(e.created_at)} for e in ticket.events]})
    return data
