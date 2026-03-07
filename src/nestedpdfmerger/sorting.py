"""Sorting utilities for PDF and directory paths."""

from __future__ import annotations

from pathlib import Path

from natsort import natsort_keygen

from .config import VALID_SORT_MODES

_natkey = natsort_keygen()


def _natural_key(p: Path) -> tuple:
    return _natkey(p.name)


def _alpha_key(p: Path) -> str:
    return p.name.lower()


def _mtime_key(p: Path) -> float:
    try:
        return p.stat().st_mtime
    except OSError:
        return 0.0


_SORT_FUNCS = {
    "natural": _natural_key,
    "alpha": _alpha_key,
    "mtime": _mtime_key,
}


def sort_paths(
    paths: list[Path],
    mode: str = "natural",
    reverse: bool = False,
) -> list[Path]:
    """Sort a list of Path objects by the given mode.

    Args:
        paths: Paths to sort.
        mode: One of 'natural', 'alpha', or 'mtime'.
        reverse: If True, reverse the sort order.

    Returns:
        A new sorted list of paths.

    Raises:
        ValueError: If mode is not a recognised sort mode.
    """
    if mode not in VALID_SORT_MODES:
        raise ValueError(
            f"Unknown sort mode {mode!r}. Valid options: {list(VALID_SORT_MODES)}"
        )
    return sorted(paths, key=_SORT_FUNCS[mode], reverse=reverse)
