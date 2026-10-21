"""Idempotent import: retain every supplied ID, value and null, without overwriting edits."""
import json
from datetime import date
from sqlalchemy import select
from .config import settings, BACKEND_DIR
from .database import Base, engine, SessionLocal
from .models import User, Book, Ticket, AuditEvent
from .security import hash_password


def seed_data(db):
    data = json.loads((BACKEND_DIR / 'data' / 'authorcare_sample_data.json').read_text(encoding='utf-8'))
    for author in data['authors']:
        if db.get(User, author['author_id']) is None:
            db.add(User(id=author['author_id'], name=author['name'], email=author['email'].lower(),
                        phone=author['phone'], city=author['city'], joined_date=date.fromisoformat(author['joined_date']),
                        password_hash=hash_password(settings.demo_author_password), role='author'))
            db.flush()
        for book in author['books']:
            if db.get(Book, book['book_id']) is None:
                values = dict(book)
                values['id'] = values.pop('book_id')
                for field in ['publication_date', 'last_royalty_payout_date']:
                    values[field] = date.fromisoformat(values[field]) if values[field] else None
                db.add(Book(author_id=author['author_id'], **values))
    if db.get(User, 'ADMIN001') is None:
        db.add(User(id='ADMIN001', name='AuthorCare Operations', email=settings.admin_email.lower(),
                    password_hash=hash_password(settings.demo_admin_password), role='admin'))
    db.commit()


def seed_demo_tickets(db):
    # Optional scenarios are separate from the untouched author/book source dataset.
    examples = [
        ('AUTH001', 'BK001', 'Question about my pending royalty', 'My dashboard shows a pending royalty of Rs 3,570. Could you explain when this can be paid?'),
        ('AUTH002', 'BK003', 'ISBN mismatch on Amazon', 'The ISBN shown on Amazon is different from the ISBN on my physical copy. Please investigate the incorrect listing.'),
        ('AUTH003', 'BK005', 'Misprinted author copies', 'Several author copies have blurry images and misaligned pages. Can you help arrange a replacement after verification?'),
        ('AUTH007', 'BK013', 'Update on cover design', 'Could you share an update on the cover design for Midnight in Mysore and the next step for me?'),
        ('AUTH009', 'BK016', 'Why is my Rs 850 not paid yet?', 'My royalty dashboard shows Rs 850 pending and no payout so far. Please explain the payout threshold.'),
        ('AUTH010', None, 'Updating my author bio', 'Can I update my author biography and book description after the book is published?')
    ]
    from .ai import fallback_triage
    for author_id, book_id, subject, description in examples:
        exists = db.scalar(select(Ticket).where(Ticket.author_id == author_id, Ticket.subject == subject))
        if exists:
            continue
        result = fallback_triage(subject + '\n' + description)
        ticket = Ticket(author_id=author_id, book_id=book_id, subject=subject, description=description,
                        category=result.category.value, priority=result.priority.value, ai_category=result.category.value,
                        ai_priority=result.priority.value, triage_source='fallback', triage_status='fallback',
                        triage_reason=result.reason, ai_error='Optional demo ticket; rule-based initial triage.')
        db.add(ticket)
        db.flush()
        db.add(AuditEvent(ticket_id=ticket.id, actor='Demo seed', action='Optional example ticket created.'))
    db.commit()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--demo-tickets', action='store_true')
    args = parser.parse_args()
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed_data(db)
        if args.demo_tickets:
            seed_demo_tickets(db)
    print('Seed complete: 10 authors, 18 books and one admin. Existing records preserved.')
