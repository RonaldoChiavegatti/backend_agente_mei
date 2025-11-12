"""Lightweight stub for the ``email_validator`` package used in unit tests."""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

try:  # pragma: no cover - fallback for older Python versions
    import importlib.metadata as importlib_metadata
except ImportError:  # pragma: no cover
    import importlib_metadata  # type: ignore


class EmailNotValidError(ValueError):
    """Exception raised when an email address fails basic validation."""


@dataclass
class ValidatedEmail:
    email: str
    local_part: str
    domain: str
    normalized: str


def validate_email(email: str, *_, **__) -> ValidatedEmail:
    """Very small subset of the real validator behaviour."""

    if "@" not in email or email.count("@") != 1:
        raise EmailNotValidError("The email address is not valid.")

    local_part, domain = email.split("@", 1)
    if not local_part or not domain:
        raise EmailNotValidError("The email address is not valid.")

    normalized = f"{local_part}@{domain.lower()}"
    return ValidatedEmail(
        email=email,
        local_part=local_part,
        domain=domain.lower(),
        normalized=normalized,
    )


__version__ = "2.0.0"


_original_version = getattr(importlib_metadata, "version", None)
_original_distribution = getattr(importlib_metadata, "distribution", None)


def _patched_version(package_name: str) -> str:
    if package_name == "email-validator":
        return __version__
    if _original_version is None:
        raise importlib_metadata.PackageNotFoundError(package_name)
    return _original_version(package_name)


if _original_version is not None and not getattr(
    importlib_metadata.version, "__email_validator_stub__", False
):
    importlib_metadata.version = _patched_version  # type: ignore[assignment]
    setattr(importlib_metadata.version, "__email_validator_stub__", True)


def _patched_distribution(package_name: str):
    if package_name == "email-validator":
        return SimpleNamespace(version=__version__)
    if _original_distribution is None:
        raise importlib_metadata.PackageNotFoundError(package_name)
    return _original_distribution(package_name)


if _original_distribution is not None and not getattr(
    importlib_metadata.distribution, "__email_validator_stub__", False
):
    importlib_metadata.distribution = _patched_distribution  # type: ignore[assignment]
    setattr(
        importlib_metadata.distribution,
        "__email_validator_stub__",
        True,
    )


__all__ = ["EmailNotValidError", "validate_email", "ValidatedEmail"]

