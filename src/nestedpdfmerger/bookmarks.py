"""Bookmark data structure for hierarchical PDF outline entries."""

from __future__ import annotations


class Bookmark:
    """Represents a single PDF outline (bookmark) entry with optional children."""

    __slots__ = ("_page", "_title", "_children")

    def __init__(self, page: int, title: str) -> None:
        self._page = page
        self._title = title
        self._children: list[Bookmark] = []

    @property
    def page(self) -> int:
        return self._page

    @property
    def title(self) -> str:
        return self._title

    @property
    def children(self) -> list[Bookmark]:
        return self._children

    def add_child(self, child: Bookmark) -> None:
        if not isinstance(child, Bookmark):
            raise TypeError("child must be a Bookmark instance")
        self._children.append(child)

    def __repr__(self) -> str:
        return (
            f"Bookmark(page={self._page!r}, title={self._title!r},"
            f" children={len(self._children)})"
        )
