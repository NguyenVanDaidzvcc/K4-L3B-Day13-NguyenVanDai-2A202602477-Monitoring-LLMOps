from __future__ import annotations

import time
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from structlog.contextvars import bind_contextvars, clear_contextvars


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Xóa context cũ để tránh dữ liệu request trước bị rò sang request sau
        clear_contextvars()

        # Nếu client gửi x-request-id thì dùng lại.
        # Nếu không có thì sinh ID theo format req-<8 ký tự hex>
        incoming_request_id = request.headers.get("x-request-id")

        correlation_id = (
            incoming_request_id.strip()
            if incoming_request_id and incoming_request_id.strip()
            else f"req-{uuid.uuid4().hex[:8]}"
        )

        # Bind correlation_id vào structlog context
        bind_contextvars(correlation_id=correlation_id)

        # Cho endpoint truy cập correlation_id
        request.state.correlation_id = correlation_id

        start = time.perf_counter()

        response = await call_next(request)

        elapsed_ms = int((time.perf_counter() - start) * 1000)

        # Trả correlation ID và thời gian xử lý trong response header
        response.headers["x-request-id"] = correlation_id
        response.headers["x-response-time-ms"] = str(elapsed_ms)

        return response