"""Support module providing small pieces of the ``httpx._client`` API."""


class UseClientDefault:
    """Placeholder sentinel used by FastAPI's TestClient."""


USE_CLIENT_DEFAULT = UseClientDefault()


__all__ = ["UseClientDefault", "USE_CLIENT_DEFAULT"]

