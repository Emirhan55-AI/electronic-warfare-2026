"""Turkish desktop operator console package."""

from __future__ import annotations


__all__ = ["build_application", "build_quick_application", "main"]


def __getattr__(name: str) -> object:
    """Keep verification composition imports lazy at the product boundary."""
    if name == "build_application":
        from .application import build_application

        return build_application
    if name in {"build_quick_application", "main"}:
        from .quick_application import build_quick_application, main

        return build_quick_application if name == "build_quick_application" else main
    raise AttributeError(name)
