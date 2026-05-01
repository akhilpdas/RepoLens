"""Theme system for RepoLens — runtime CSS injection for light/dark/system modes.

Streamlit's `config.toml` `base` is loaded once at server startup and is not
switchable at runtime. This module supplies a runtime toggle by injecting CSS
overrides on each rerun. Selection lives in `st.session_state["theme_choice"]`.

Pure functions live here so they're testable without bootstrapping Streamlit.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

THEME_CHOICES: list[str] = ["🌞 Light", "🌙 Dark", "⚙️ System"]
DEFAULT_THEME: str = "⚙️ System"

_ASSETS_DIR = Path(__file__).parent / "assets"
THEME_CSS: dict[str, Path] = {
    "🌙 Dark": _ASSETS_DIR / "dark_theme.css",
    "🌞 Light": _ASSETS_DIR / "light_theme.css",
}


def resolve_choice(raw: str | None) -> str:
    """Return a valid choice; fall back to default for unknown/missing input."""
    if raw in THEME_CHOICES:
        return raw  # type: ignore[return-value]
    return DEFAULT_THEME


def get_css_for(choice: str) -> str | None:
    """Read the CSS file for the given choice. Returns None if the choice
    is system mode or the file is missing.
    """
    css_path = THEME_CSS.get(choice)
    if css_path is None or not css_path.exists():
        return None
    return css_path.read_text()


def apply_theme() -> None:
    """Inject the CSS for the currently selected theme.

    Reads `st.session_state["theme_choice"]`. System mode = no-op.
    Missing CSS files = no-op (graceful fallback to Streamlit defaults).
    """
    choice = resolve_choice(st.session_state.get("theme_choice"))
    css = get_css_for(choice)
    if css:
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
