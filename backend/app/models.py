"""Explicit ownership and private/public message boundaries live in the schema."""
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4
from sqlalchemy import Date, DateTime, ForeignKey, String, Text, Numeric, JSON, Index, Boolean, LargeBinary
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def new_id():
    return str(uuid4())


class User(Base):
    __tablename__ = 'users'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(150))
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(300))
    role: Mapped[str] = mapped_column(String(10))
    phone: Mapped[str | None] = mapped_column(String(30))
    city: Mapped[str | None] = mapped_column(String(100))
    joined_date: Mapped[date | None] = mapped_column(Date)


class Book(Base):
    __tablename__ = 'books'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    author_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    title: Mapped[str] = mapped_column(String(250))
    isbn: Mapped[str] = mapped_column(String(50))
    genre: Mapped[str] = mapped_column(String(150))
    publication_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(100))
    mrp: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    author_royalty_per_copy: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    total_copies_sold: Mapped[int] = mapped_column(default=0)
    total_royalty_earned: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    royalty_paid: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    royalty_pending: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    last_royalty_payout_date: Mapped[date | None] = mapped_column(Date)
    print_partner: Mapped[str | None] = mapped_column(String(60))
    available_on: Mapped[list] = mapped_column(JSON, default=list)


class Ticket(Base):
    __tablename__ = 'tickets'
    __table_args__ = (Index('ix_ticket_queue', 'status', 'priority', 'created_at'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    author_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    book_id: Mapped[str | None] = mapped_column(ForeignKey('books.id'), index=True)
    subject: Mapped[str] = mapped_column(String(180))
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default='Open')
    category: Mapped[str] = mapped_column(String(80), default='General Inquiry')
    priority: Mapped[str] = mapped_column(String(10), default='Medium')
    assigned_to: Mapped[str | None] = mapped_column(ForeignKey('users.id'))
    category_overridden: Mapped[bool] = mapped_column(Boolean, default=False)
    priority_overridden: Mapped[bool] = mapped_column(Boolean, default=False)
    triage_status: Mapped[str] = mapped_column(String(20), default='pending')
    triage_source: Mapped[str] = mapped_column(String(20), default='pending')
    triage_reason: Mapped[str | None] = mapped_column(Text)
    ai_category: Mapped[str | None] = mapped_column(String(80))
    ai_priority: Mapped[str | None] = mapped_column(String(10))
    ai_error: Mapped[str | None] = mapped_column(String(120))
    draft_text: Mapped[str | None] = mapped_column(Text)
    draft_source: Mapped[str | None] = mapped_column(String(20))
    draft_context_hash: Mapped[str | None] = mapped_column(String(64))
    draft_review_notes: Mapped[str | None] = mapped_column(Text)
    draft_generated_at: Mapped[datetime | None] = mapped_column(DateTime)
    ai_input_tokens: Mapped[int] = mapped_column(default=0)
    ai_output_tokens: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    version: Mapped[int] = mapped_column(default=1, nullable=False)
    __mapper_args__ = {'version_id_col': version}
    author: Mapped[User] = relationship(foreign_keys=[author_id])
    assignee: Mapped[User | None] = relationship(foreign_keys=[assigned_to])
    book: Mapped[Book | None] = relationship()
    messages: Mapped[list['Message']] = relationship(order_by='Message.created_at', cascade='all, delete-orphan')
    events: Mapped[list['AuditEvent']] = relationship(order_by='AuditEvent.created_at', cascade='all, delete-orphan')
    attachments: Mapped[list['Attachment']] = relationship(order_by='Attachment.created_at', cascade='all, delete-orphan')


class Attachment(Base):
    __tablename__ = 'attachments'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    ticket_id: Mapped[str] = mapped_column(ForeignKey('tickets.id'), index=True)
    uploaded_by: Mapped[str] = mapped_column(ForeignKey('users.id'))
    filename: Mapped[str] = mapped_column(String(180))
    content_type: Mapped[str] = mapped_column(String(50))
    size_bytes: Mapped[int] = mapped_column()
    # Small, bounded demo uploads share the database's persistence and access controls.
    # Deferred loading keeps file bytes out of ticket queries and AI context.
    content: Mapped[bytes] = mapped_column(LargeBinary, deferred=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Message(Base):
    __tablename__ = 'messages'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    ticket_id: Mapped[str] = mapped_column(ForeignKey('tickets.id'), index=True)
    sender_id: Mapped[str] = mapped_column(ForeignKey('users.id'))
    kind: Mapped[str] = mapped_column(String(10))
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    sender: Mapped[User] = relationship()


class AuditEvent(Base):
    __tablename__ = 'audit_events'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    ticket_id: Mapped[str] = mapped_column(ForeignKey('tickets.id'), index=True)
    actor: Mapped[str] = mapped_column(String(150))
    action: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
