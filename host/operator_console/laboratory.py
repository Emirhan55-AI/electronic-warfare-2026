"""Validation-only application composition, excluded from the product package."""

from __future__ import annotations

from typing import Any

from host.acquisition.mock import DeterministicMockBackend

from .application import build_application


def build_laboratory_application(argv: list[str] | None = None, **kwargs: Any):
    """Build the offline verification UI with mock and training capabilities."""

    kwargs.setdefault("laboratory_mode", True)
    kwargs.setdefault("test_backend_factory", DeterministicMockBackend)
    return build_application(argv, **kwargs)


__all__ = ["build_laboratory_application"]
