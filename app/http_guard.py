"""
HTTP middleware helpers for guarding MCP transports with a static header.
"""

from __future__ import annotations

from dataclasses import dataclass

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


@dataclass(frozen=True)
class HeaderGuardConfig:
    """Configuration for validating an incoming HTTP header."""

    name: str
    value: str


class HeaderValidationMiddleware(BaseHTTPMiddleware):
    """
    Rejects HTTP requests that do not carry the expected header/value pair.

    This middleware is transport-agnostic and therefore works for both SSE and
    Streamable HTTP servers that Starlette spins up inside FastMCP.
    """

    def __init__(self, app, guard: HeaderGuardConfig):
        super().__init__(app)
        self._guard = guard

    async def dispatch(self, request: Request, call_next):
        presented = request.headers.get(self._guard.name)
        if presented != 'Bearer ' + self._guard.value:
            return JSONResponse(
                {"error": "missing or invalid request header"},
                status_code=403,
            )
        return await call_next(request)
