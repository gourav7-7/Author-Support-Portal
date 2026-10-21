import hashlib
import hmac
import secrets
from collections import OrderedDict
from datetime import datetime, timedelta, timezone
from threading import Lock
from time import monotonic
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from .config import settings
from .database import get_db
from .models import User


def hash_password(password: str):
    salt = secrets.token_bytes(16)
    value = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1, dklen=32)
    return f'scrypt${salt.hex()}${value.hex()}'


def verify_password(password: str, encoded: str):
    try:
        algorithm, salt, expected = encoded.split('$')
        if algorithm != 'scrypt':
            return False
        actual = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1, dklen=32)
        return hmac.compare_digest(actual.hex(), expected)
    except (ValueError, TypeError):
        return False


def create_token(user: User):
    now = datetime.now(timezone.utc)
    return jwt.encode({'sub': user.id, 'iat': now, 'exp': now + timedelta(minutes=settings.token_expire_minutes),
                       'iss': 'bookleaf-support', 'aud': 'bookleaf-portal', 'jti': secrets.token_hex(16)},
                      settings.jwt_secret, algorithm='HS256')


bearer = HTTPBearer(auto_error=False)


def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)):
    invalid = HTTPException(401, 'Please sign in again.', headers={'WWW-Authenticate': 'Bearer'})
    if credentials is None:
        raise invalid
    try:
        payload = jwt.decode(credentials.credentials, settings.jwt_secret, algorithms=['HS256'],
                             issuer='bookleaf-support', audience='bookleaf-portal',
                             options={'require': ['exp', 'iat', 'sub', 'jti']})
        user = db.get(User, payload['sub'])
    except (jwt.InvalidTokenError, KeyError):
        raise invalid
    if user is None:
        raise invalid
    return user


def admin_user(user: User = Depends(current_user)):
    if user.role != 'admin':
        raise HTTPException(403, 'Administrator access required.')
    return user


class RateLimiter:
    """Bounded, process-local demo limit; a shared store is needed for multi-worker production."""
    def __init__(self):
        self.entries = OrderedDict()
        self.lock = Lock()

    def check(self, key: str, limit: int, window: int = 60):
        now = monotonic()
        with self.lock:
            attempts = [t for t in self.entries.pop(key, []) if t > now - window]
            if len(attempts) >= limit:
                self.entries[key] = attempts
                raise HTTPException(429, 'Too many requests. Please try again in a minute.', headers={'Retry-After': str(window)})
            attempts.append(now)
            self.entries[key] = attempts
            while len(self.entries) > 10000:
                self.entries.popitem(last=False)


limiter = RateLimiter()
