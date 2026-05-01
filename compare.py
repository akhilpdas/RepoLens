"""Multi-repo comparison helpers — session-state namespacing.

When compare mode is enabled, two pipelines run in parallel columns. Each needs
its own session-state namespace so the stage machines don't collide. This
module provides a tiny keyer pattern: pass `slot=None` for canonical keys
(single-repo mode, backwards-compatible) or `slot="a" | "b"` for namespaced
keys (compare mode).

Pure functions — no Streamlit imports — so this is fully unit-testable.
"""

from __future__ import annotations

from typing import Any, Iterable, MutableMapping

# Keys that participate in the stage machine. Anything in this list gets
# namespaced when slot is provided. New keys must be added here.
PIPELINE_KEYS: tuple[str, ...] = (
    "stage",
    "active_question",
    "draft",
    "final_state",
    "retriever",
    "evidence_chunks",
    "trace",
    "last_review",
    "force_reindex",
    "session",
)

# Valid slot identifiers in compare mode.
SLOTS: tuple[str, ...] = ("a", "b")


def slot_key(base: str, slot: str | None = None) -> str:
    """Return the namespaced key for `base`.

    >>> slot_key("stage")
    'stage'
    >>> slot_key("stage", "a")
    'stage_a'
    >>> slot_key("stage", "b")
    'stage_b'
    """
    if slot is None:
        return base
    if slot not in SLOTS:
        raise ValueError(f"slot must be one of {SLOTS!r} or None; got {slot!r}")
    return f"{base}_{slot}"


def ss_get(state: MutableMapping[str, Any], base: str,
           slot: str | None = None, default: Any = None) -> Any:
    """Read `base` from `state`, namespaced by `slot` if given."""
    return state.get(slot_key(base, slot), default)


def ss_set(state: MutableMapping[str, Any], base: str, value: Any,
           slot: str | None = None) -> None:
    """Write `value` to `base` in `state`, namespaced by `slot` if given."""
    state[slot_key(base, slot)] = value


def ss_pop(state: MutableMapping[str, Any], base: str,
           slot: str | None = None, default: Any = None) -> Any:
    """Pop `base` from `state`, namespaced by `slot` if given."""
    return state.pop(slot_key(base, slot), default)


def reset_slot(state: MutableMapping[str, Any], slot: str | None = None,
               keys: Iterable[str] = PIPELINE_KEYS) -> None:
    """Clear all pipeline keys for the given slot.

    Used by the "🆕 New question" button. In compare mode call this for both
    "a" and "b". In single-repo mode call with slot=None to clear canonical
    keys.
    """
    for base in keys:
        state.pop(slot_key(base, slot), None)


def reset_all_slots(state: MutableMapping[str, Any],
                    keys: Iterable[str] = PIPELINE_KEYS) -> None:
    """Clear pipeline keys across single-repo and both compare slots."""
    keys = tuple(keys)
    reset_slot(state, slot=None, keys=keys)
    for s in SLOTS:
        reset_slot(state, slot=s, keys=keys)


def slot_label(slot: str | None) -> str:
    """Human-readable label for a slot (used in UI titles)."""
    return {None: "", "a": "🅰️ ", "b": "🅱️ "}[slot]


def widget_key(base: str, slot: str | None = None) -> str:
    """Streamlit widget keys must be unique across reruns. In compare mode
    we suffix them with the slot so widgets in column A don't collide with
    column B.
    """
    return slot_key(base, slot)
