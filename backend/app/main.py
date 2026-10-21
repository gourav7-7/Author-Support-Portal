import logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm.exc import StaleDataError
from .api import router
from .config import settings, ROOT_DIR
from .database import Base, engine, SessionLocal
from .seed import seed_data
from .ai import recover_interrupted_triage
from .attachments import MAX_ATTACHMENT_BYTES

logging.basicConfig(level=logging.INFO, format='%(levelname)s %(name)s %(message)s')


@asynccontextmanager
async def lifespan(app):
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        if settings.auto_seed:
            seed_data(db)
        recover_interrupted_triage(db)
    yield


app = FastAPI(title='BookLeaf Author Support API', version='1.1.0', lifespan=lifespan,
              description='Author and admin support portal. Login at /api/auth/login, then use Authorize with the returned bearer token.')
app.add_middleware(CORSMiddleware, allow_origins=[x.strip() for x in settings.cors_origins.split(',') if x.strip()],
                   allow_credentials=False, allow_methods=['GET', 'POST', 'PATCH'], allow_headers=['Authorization', 'Content-Type'])
app.include_router(router)


@app.middleware('http')
async def security_headers(request: Request, call_next):
    try:
        length = int(request.headers.get('content-length', '0') or 0)
    except ValueError:
        return JSONResponse({'error': {'code': 'bad_request', 'message': 'Invalid Content-Length.'}}, status_code=400)
    upload = request.method == 'POST' and request.url.path.startswith('/api/tickets/') and request.url.path.endswith('/attachments')
    if length < 0:
        return JSONResponse({'error': {'code': 'bad_request', 'message': 'Invalid Content-Length.'}}, status_code=400)
    if length > (MAX_ATTACHMENT_BYTES if upload else 100_000):
        return JSONResponse({'error': {'code': 'request_too_large', 'message': 'Request body is too large.'}}, status_code=413)
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'same-origin'
    if request.url.path.startswith('/api'):
        response.headers['Cache-Control'] = 'no-store'
    elif not request.url.path.startswith(('/docs', '/redoc', '/openapi')):
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'"
    return response


@app.exception_handler(HTTPException)
async def http_error(request, exc):
    return JSONResponse({'error': {'code': f'http_{exc.status_code}', 'message': str(exc.detail)}}, status_code=exc.status_code, headers=exc.headers)


@app.exception_handler(RequestValidationError)
async def validation_error(request, exc):
    # Do not echo password/body contents in validation responses.
    errors = [{'field': '.'.join(map(str, e['loc'])), 'message': e['msg']} for e in exc.errors()]
    return JSONResponse({'error': {'code': 'validation_error', 'message': 'Please check the submitted fields.', 'details': errors}}, status_code=422)


@app.exception_handler(StaleDataError)
async def stale_error(request, exc):
    return JSONResponse({'error': {'code': 'conflict', 'message': 'This ticket changed. Refresh and try again.'}}, status_code=409)


@app.exception_handler(IntegrityError)
async def integrity_error(request, exc):
    return JSONResponse({'error': {'code': 'conflict', 'message': 'This operation conflicts with existing data.'}}, status_code=409)


@app.exception_handler(OperationalError)
async def database_error(request, exc):
    return JSONResponse({'error': {'code': 'database_unavailable', 'message': 'The database is temporarily unavailable. Please retry.'}}, status_code=503)


@app.exception_handler(Exception)
async def unexpected_error(request, exc):
    logging.getLogger(__name__).error('Unhandled application error: %s', type(exc).__name__)
    return JSONResponse({'error': {'code': 'server_error', 'message': 'An unexpected error occurred. Please retry.'}}, status_code=500)


@app.get('/health', tags=['Health'])
def health():
    with SessionLocal() as db:
        db.execute(text('SELECT 1'))
    return {'status': 'ok'}


# The production image serves the compiled React app and API from the same origin.
dist = Path(settings.frontend_dist) if settings.frontend_dist else ROOT_DIR / 'frontend' / 'dist'
if (dist / 'index.html').is_file():
    app.mount('/assets', StaticFiles(directory=dist / 'assets'), name='assets')

    @app.get('/{path:path}', include_in_schema=False)
    def spa(path: str):
        if path == 'api' or path.startswith('api/'):
            raise HTTPException(404, 'API endpoint not found.')
        return FileResponse(dist / 'index.html')
