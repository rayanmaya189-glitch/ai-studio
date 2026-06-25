"""ASGI middleware: request-id propagation and access logging.

Kept dependency-free. The request-id is stored in a contextvar (see
``logging_config.request_id_var``) so every log line emitted while handling the
request is automatically correlated, and is echoed back in the ``X-Request-ID``
response header.
"""

from __future__ import annotations

import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.logging_config import request_id_var

_access_logger = logging.getLogger("ads.access")

_REQUEST_ID_HEADER = "X-Request-ID"


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        incoming = request.headers.get(_REQUEST_ID_HEADER)
        request_id = incoming or uuid.uuid4().hex
        token = request_id_var.set(request_id)
        request.state.request_id = request_id

        start = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers[_REQUEST_ID_HEADER] = request_id
            return response
        finally:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            _access_logger.info(
                "request",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status": status_code,
                    "duration_ms": duration_ms,
                    "client": request.client.host if request.client else None,
                },
            )
            request_id_var.reset(token)
