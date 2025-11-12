"""Comprehensive local stub for the ``httpx`` package used in unit tests.

This stub covers only the sync functionality required by FastAPI's
``TestClient``. It is **not** a drop-in replacement for the real library but it
implements just enough of the public API to exercise the project code in a
controlled environment without network access.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Iterator, List, Mapping, MutableMapping, Optional, Sequence, Tuple
from urllib.parse import urlencode, urljoin, urlsplit


class RequestError(Exception):
    """Base exception mimicking ``httpx.RequestError``."""


class HTTPStatusError(RequestError):
    """Exception raised when a response status code indicates an error."""

    def __init__(self, message: str, *, response: "Response"):
        super().__init__(message)
        self.response = response


class Headers:
    """Minimal representation of ``httpx.Headers`` with multi-value support."""

    def __init__(self, data: Optional[Mapping[str, Any]] = None):
        self._items: List[Tuple[str, str]] = []
        if data:
            self.update(data)

    def update(self, data: Mapping[str, Any]) -> None:
        for key, value in data.items():
            if isinstance(value, (list, tuple)):
                for item in value:
                    self._items.append((key.lower(), str(item)))
            else:
                self._items.append((key.lower(), str(value)))

    def multi_items(self) -> List[Tuple[str, str]]:
        return list(self._items)

    def __contains__(self, key: str) -> bool:
        key_lower = key.lower()
        return any(existing_key == key_lower for existing_key, _ in self._items)

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        key_lower = key.lower()
        for existing_key, value in reversed(self._items):
            if existing_key == key_lower:
                return value
        return default

    def setdefault(self, key: str, value: str) -> None:
        if key not in self:
            self._items.append((key.lower(), value))


class URL:
    """Simplified ``httpx.URL`` implementation."""

    def __init__(self, url: str):
        self._url = url
        parsed = urlsplit(url)
        self.scheme = parsed.scheme or "http"
        netloc = parsed.netloc or ""
        self.netloc = netloc.encode("ascii", errors="ignore")
        path = parsed.path or "/"
        self.path = path
        self.raw_path = path.encode("ascii", errors="ignore")
        query = parsed.query or ""
        self.query = query.encode("ascii", errors="ignore")

    def __str__(self) -> str:
        return self._url


class Request:
    """Greatly simplified request object."""

    def __init__(
        self,
        method: str,
        url: URL,
        *,
        headers: Optional[Headers] = None,
        content: Optional[bytes] = None,
        extensions: Optional[MutableMapping[str, Any]] = None,
    ) -> None:
        self.method = method.upper()
        self.url = url
        self.headers = headers or Headers()
        self._content = content or b""
        self.extensions = extensions or {}

    def read(self) -> bytes:
        return self._content


@dataclass
class ByteStream:
    data: bytes

    def read(self) -> bytes:
        return self.data


class Response:
    def __init__(
        self,
        status_code: int = 200,
        headers: Optional[Sequence[Tuple[str, str]]] = None,
        stream: Optional[ByteStream] = None,
        request: Optional[Request] = None,
    ) -> None:
        self.status_code = status_code
        self.headers = headers or []
        self._stream = stream or ByteStream(b"")
        self.request = request
        self._body = self._stream.read()
        try:
            self.text = self._body.decode("utf-8")
        except UnicodeDecodeError:
            self.text = ""

    def json(self) -> Any:
        if not self.text:
            return {}
        return json.loads(self.text)

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise HTTPStatusError(
                f"HTTP request failed with status code {self.status_code}",
                response=self,
            )


class BaseTransport:
    """Base class for transports compatible with the real httpx API."""

    def handle_request(self, request: Request) -> Response:  # pragma: no cover - interface
        raise NotImplementedError


class _NullTransport(BaseTransport):
    def handle_request(self, request: Request) -> Response:  # pragma: no cover - fallback
        raise RequestError(
            "No transport backend is configured in the lightweight httpx stub."
        )


class Client:
    """Minimal synchronous client that delegates requests to a transport."""

    def __init__(
        self,
        *,
        base_url: str = "",
        headers: Optional[Mapping[str, Any]] = None,
        transport: Optional[BaseTransport] = None,
        follow_redirects: bool = True,
        cookies: Optional[Mapping[str, Any]] = None,
    ) -> None:
        self.base_url = base_url
        self._transport = transport or _NullTransport()
        self.follow_redirects = follow_redirects
        self.cookies = dict(cookies or {})
        self._default_headers = Headers(headers)

    # -- context manager -------------------------------------------------
    def __enter__(self) -> "Client":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[override]
        self.close()

    def close(self) -> None:
        pass

    # -- helpers ---------------------------------------------------------
    def _merge_url(self, url: Any) -> URL:
        if isinstance(url, URL):
            return url

        url_str = str(url)
        if self.base_url and not url_str.startswith(("http://", "https://", "ws://", "wss://")):
            url_str = urljoin(self.base_url, url_str)
        return URL(url_str)

    def _prepare_content(
        self,
        *,
        content: Optional[bytes] = None,
        data: Optional[Mapping[str, Any]] = None,
        json_data: Any = None,
    ) -> Tuple[Optional[bytes], Optional[str]]:
        if json_data is not None:
            return json.dumps(json_data).encode("utf-8"), "application/json"
        if data is not None:
            return urlencode(data, doseq=True).encode("utf-8"), "application/x-www-form-urlencoded"
        return content, None

    def request(
        self,
        method: str,
        url: Any,
        *,
        content: Optional[bytes] = None,
        data: Optional[Mapping[str, Any]] = None,
        files: Any = None,
        json: Any = None,
        params: Optional[Mapping[str, Any]] = None,
        headers: Optional[Mapping[str, Any]] = None,
        cookies: Optional[Mapping[str, Any]] = None,
        auth: Any = None,
        follow_redirects: Any = None,
        timeout: Any = None,
        extensions: Optional[MutableMapping[str, Any]] = None,
    ) -> Response:
        del files, cookies, auth, follow_redirects, timeout  # Not implemented in the stub

        merged_url = self._merge_url(url)
        body, content_type = self._prepare_content(content=content, data=data, json_data=json)

        request_headers = Headers()
        request_headers.update({key: value for key, value in self._default_headers.multi_items()})
        if headers:
            request_headers.update(headers)
        if content_type and "content-type" not in request_headers:
            request_headers.setdefault("content-type", content_type)

        if params:
            query_string = urlencode(params, doseq=True)
            if merged_url.query:
                query_string = f"{merged_url.query.decode()}&{query_string}"
            new_url = f"{str(merged_url)}?{query_string}" if query_string else str(merged_url)
            merged_url = URL(new_url)

        request = Request(method, merged_url, headers=request_headers, content=body, extensions=extensions)
        response = self._transport.handle_request(request)
        return response

    # Convenience HTTP verb helpers -------------------------------------
    def get(self, url: Any, **kwargs: Any) -> Response:
        return self.request("GET", url, **kwargs)

    def post(self, url: Any, **kwargs: Any) -> Response:
        return self.request("POST", url, **kwargs)

    def put(self, url: Any, **kwargs: Any) -> Response:
        return self.request("PUT", url, **kwargs)

    def patch(self, url: Any, **kwargs: Any) -> Response:
        return self.request("PATCH", url, **kwargs)

    def delete(self, url: Any, **kwargs: Any) -> Response:
        return self.request("DELETE", url, **kwargs)

    def options(self, url: Any, **kwargs: Any) -> Response:
        return self.request("OPTIONS", url, **kwargs)

    def head(self, url: Any, **kwargs: Any) -> Response:
        return self.request("HEAD", url, **kwargs)


__all__ = [
    "BaseTransport",
    "ByteStream",
    "Client",
    "Headers",
    "HTTPStatusError",
    "Request",
    "RequestError",
    "Response",
    "URL",
]


# Re-export helper modules expected by Starlette/FastAPI.
from . import _client, _types  # noqa: E402  (import at end of file)


