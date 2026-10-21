from enum import Enum
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator


class Category(str, Enum):
    royalty = 'Royalty & Payments'
    isbn = 'ISBN & Metadata Issues'
    printing = 'Printing & Quality'
    distribution = 'Distribution & Availability'
    production = 'Book Status & Production Updates'
    general = 'General Inquiry'


class Priority(str, Enum):
    critical = 'Critical'
    high = 'High'
    medium = 'Medium'
    low = 'Low'


class Status(str, Enum):
    open = 'Open'
    progress = 'In Progress'
    resolved = 'Resolved'
    closed = 'Closed'


class InputModel(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)


class Login(InputModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=False)
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=128)

    @field_validator('email')
    @classmethod
    def email_format(cls, value):
        value = value.strip()
        if '@' not in value or any(c.isspace() for c in value):
            raise ValueError('Enter a valid email address.')
        return value.lower()


class TicketCreate(InputModel):
    book_id: str | None = Field(default=None, max_length=36)
    subject: str = Field(min_length=3, max_length=180)
    description: str = Field(min_length=10, max_length=6000)


class TicketUpdate(InputModel):
    version: int = Field(ge=1)
    status: Status | None = None
    category: Category | None = None
    priority: Priority | None = None
    assignment: Literal['self', 'unassign'] | None = None


class MessageCreate(InputModel):
    body: str = Field(min_length=1, max_length=6000)
    version: int = Field(ge=1)
    kind: Literal['reply', 'note'] = 'reply'
    resolve: bool = False


class DraftRequest(InputModel):
    force: bool = False


class TriageResult(BaseModel):
    model_config = ConfigDict(extra='forbid')
    category: Category
    priority: Priority
    reason: str = Field(min_length=1, max_length=500)


class DraftResult(BaseModel):
    model_config = ConfigDict(extra='forbid')
    reply: str = Field(min_length=10, max_length=6000)
    review_notes: str = Field(max_length=1200)
