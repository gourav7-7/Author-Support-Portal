"""Bounded binary uploads; file contents are never passed to the language model."""
from pathlib import PurePosixPath
from fastapi import HTTPException, Request

MAX_ATTACHMENT_BYTES = 5 * 1024 * 1024
MAX_ATTACHMENTS = 3
FILE_TYPES = {
    '.png': ('image/png', b'\x89PNG\r\n\x1a\n'),
    '.jpg': ('image/jpeg', b'\xff\xd8\xff'),
    '.jpeg': ('image/jpeg', b'\xff\xd8\xff'),
    '.pdf': ('application/pdf', b'%PDF-'),
}


async def read_attachment(request: Request, filename: str):
    filename = PurePosixPath(filename.replace('\\', '/')).name.strip()
    if not filename or len(filename) > 180 or any(ord(c) < 32 or ord(c) == 127 for c in filename):
        raise HTTPException(422, 'Use a filename of 1–180 characters without control characters.')
    file_type = FILE_TYPES.get(PurePosixPath(filename).suffix.lower())
    if not file_type:
        raise HTTPException(415, 'Attachments must be PNG, JPEG or PDF files.')
    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > MAX_ATTACHMENT_BYTES:
            raise HTTPException(413, 'Each attachment must be 5 MiB or smaller.')
        body.extend(chunk)
    if not body:
        raise HTTPException(422, 'The selected file is empty.')
    content_type, signature = file_type
    if not body.startswith(signature):
        raise HTTPException(415, 'The file contents do not match its PNG, JPEG or PDF extension.')
    return filename, content_type, bytes(body)
