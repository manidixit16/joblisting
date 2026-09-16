"""Pick a generator backend based on config, with graceful fallback."""
from __future__ import annotations

from ...config import get_settings
from .base import DocumentGenerator
from .template import TemplateGenerator


def get_generator(backend: str | None = None) -> DocumentGenerator:
    """Resolve a generator.

    backend: "template" | "claude" | "auto" (default from settings).
    - "claude" falls back to template if the key/package is unavailable.
    - "auto"   uses Claude when a key is present, else template.
    """
    s = get_settings()
    choice = (backend or s.generator_backend or "auto").lower()

    if choice == "template":
        return TemplateGenerator()

    if choice in {"claude", "auto"}:
        if s.claude_available:
            try:
                from .claude import ClaudeGenerator  # noqa: WPS433 (lazy import)

                return ClaudeGenerator()
            except Exception:
                # anthropic package missing or import error -> fall back
                return TemplateGenerator()
        # No key: "auto" falls back silently; "claude" also falls back safely.
        return TemplateGenerator()

    return TemplateGenerator()
