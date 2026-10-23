"""Browser request guards and bounded input for the loopback service.

The client header is a CSRF/preflight guard, not a secret or authentication.
Native local processes remain within the service's trust boundary.
"""

from __future__ import annotations

from starlette.datastructures import Headers
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from app.backup import MAX_BACKUP_BYTES

ALLOWED_ORIGINS = (
    "tauri://localhost",
    "http://tauri.localhost",
    "http://localhost:1420",
    "http://127.0.0.1:1420",
)
CLIENT_HEADER = "X-YomiMado-Client"
CLIENT_HEADER_VALUE = "desktop"
MAX_OCR_REQUEST_BYTES = 32 * 1024 * 1024
MAX_JSON_REQUEST_BYTES = 1024 * 1024
MAX_CAPTURE_PIXELS = 40_000_000
MAX_CAPTURE_SIDE = 16_384


def validate_capture_dimensions(width: int, height: int) -> None:
    if (
        width <= 0
        or height <= 0
        or max(width, height) > MAX_CAPTURE_SIDE
        or width * height > MAX_CAPTURE_PIXELS
    ):
        raise ValueError("Capture dimensions exceed the limit; select a smaller area")


class LocalRequestMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        origins = headers.getlist("origin")
        if len(origins) > 1 or (origins and origins[0] not in ALLOWED_ORIGINS):
            await JSONResponse({"detail": "Untrusted request origin"}, status_code=403)(
                scope, receive, send
            )
            return
        if scope["path"].startswith("/api/") and headers.getlist(CLIENT_HEADER) != [
            CLIENT_HEADER_VALUE
        ]:
            await JSONResponse({"detail": "Missing application request header"}, status_code=403)(
                scope, receive, send
            )
            return

        if scope["path"] == "/api/v1/ocr":
            limit = MAX_OCR_REQUEST_BYTES
        elif scope["path"] in ("/api/v1/backup/preview", "/api/v1/backup/restore"):
            limit = MAX_BACKUP_BYTES
        else:
            limit = MAX_JSON_REQUEST_BYTES
        lengths = headers.getlist("content-length")
        try:
            declared_length = int(lengths[0]) if lengths else 0
            if len(lengths) > 1 or declared_length < 0:
                raise ValueError
        except ValueError:
            await JSONResponse({"detail": "Invalid Content-Length"}, status_code=400)(
                scope, receive, send
            )
            return
        if declared_length > limit:
            await self._too_large(scope, receive, send)
            return

        # Bound the actual stream before JSON/multipart parsing, including requests
        # with no Content-Length or a dishonest smaller value. Buffering here avoids
        # partially parsed/spooled uploads and endpoint side effects on rejection.
        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            chunk = message.get("body", b"")
            if len(body) + len(chunk) > limit:
                await self._too_large(scope, receive, send)
                return
            body.extend(chunk)
            if not message.get("more_body", False):
                break

        delivered = False

        async def bounded_receive():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()

        await self.app(scope, bounded_receive, send)

    @staticmethod
    async def _too_large(scope: Scope, receive: Receive, send: Send) -> None:
        message = (
            "The backup exceeds the 16 MiB size limit"
            if scope["path"].startswith("/api/v1/backup/")
            else "Request exceeds the size limit; select a smaller area"
        )
        await JSONResponse({"detail": message}, status_code=413)(scope, receive, send)
