"""Simplified Vector type compatible with SQLAlchemy for tests."""

from __future__ import annotations

from typing import Any, Iterable

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.types import Float, TypeDecorator


class Vector(TypeDecorator):
    """Fallback implementation that stores vectors as ARRAY(Float)."""

    impl = ARRAY(Float)
    cache_ok = True

    class comparator_factory(TypeDecorator.Comparator):
        def cosine_distance(self, other: Iterable[float]):  # type: ignore[override]
            return func.cosine_distance(self.expr, other)

    def __init__(self, size: int) -> None:
        super().__init__()
        self.size = size

    def process_bind_param(self, value: Any, dialect):  # type: ignore[override]
        if value is None:
            return None
        return list(value)

    def copy(self, **kw):  # type: ignore[override]
        return Vector(self.size)
