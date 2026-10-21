"""One configuration source for local development, Docker and PostgreSQL."""
from pathlib import Path
import secrets
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT_DIR / '.env', extra='ignore')
    app_env: str = 'development'
    database_url: str = ''
    jwt_secret: str = ''
    token_expire_minutes: int = 480
    auto_seed: bool = True
    admin_email: str = 'admin@bookleaf.demo'
    demo_author_password: str = 'AuthorDemo!2026'
    demo_admin_password: str = 'AdminDemo!2026'
    openai_api_key: str = ''
    openai_model: str = 'gpt-4o-mini'
    ai_timeout_seconds: float = 12
    cors_origins: str = 'http://localhost:5173,http://127.0.0.1:5173'
    frontend_dist: str = ''

    def initialize(self):
        if not self.database_url:
            (BACKEND_DIR / 'data').mkdir(exist_ok=True)
            self.database_url = f"sqlite:///{(BACKEND_DIR / 'data' / 'bookleaf.db').as_posix()}"
        if self.database_url.startswith(('postgres://', 'postgresql://')):
            self.database_url = self.database_url.replace('postgres://', 'postgresql+psycopg://', 1).replace('postgresql://', 'postgresql+psycopg://', 1)
        if not self.jwt_secret:
            if self.app_env == 'production':
                raise ValueError('JWT_SECRET must be set in production (at least 32 characters).')
            secret_file = ROOT_DIR / '.local-secret'
            try:
                with secret_file.open('x', encoding='utf-8') as f:
                    f.write(secrets.token_urlsafe(48))
                secret_file.chmod(0o600)
            except FileExistsError:
                pass
            self.jwt_secret = secret_file.read_text(encoding='utf-8').strip()
        if len(self.jwt_secret) < 32:
            raise ValueError('JWT_SECRET must contain at least 32 characters.')
        if self.token_expire_minutes < 1 or self.ai_timeout_seconds <= 0:
            raise ValueError('Timeouts must be positive.')
        return self


settings = Settings().initialize()
