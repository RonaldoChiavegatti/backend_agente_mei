"""Typing helpers referenced by FastAPI's TestClient."""

from __future__ import annotations

from typing import Any, Mapping


URLTypes = Any
RequestContent = Any
RequestFiles = Any
QueryParamTypes = Mapping[str, Any] | None
HeaderTypes = Mapping[str, Any] | None
CookieTypes = Mapping[str, Any] | None
AuthTypes = Any
TimeoutTypes = Any


__all__ = [
    "URLTypes",
    "RequestContent",
    "RequestFiles",
    "QueryParamTypes",
    "HeaderTypes",
    "CookieTypes",
    "AuthTypes",
    "TimeoutTypes",
]

