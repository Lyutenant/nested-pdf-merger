"""Core PDF merging logic for nestedpdfmerger."""

from __future__ import annotations

import logging
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.errors import PdfReadError

from .bookmarks import Bookmark
from .config import DEFAULT_EXCLUDE_HIDDEN, DEFAULT_SORT_MODE
from .errors import EncryptedPDFError, MergeError
from .sorting import sort_paths

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _dir_has_pdfs(
    directory: Path,
    exclude: set[str],
    exclude_hidden: bool,
) -> bool:
    """Return True if *directory* or any subdirectory contains at least one PDF."""
    try:
        for entry in directory.iterdir():
            if exclude_hidden and entry.name.startswith("."):
                continue
            if entry.name in exclude:
                continue
            if entry.is_file() and entry.suffix.lower() == ".pdf":
                return True
            if entry.is_dir() and _dir_has_pdfs(entry, exclude, exclude_hidden):
                return True
    except PermissionError:
        pass
    return False


def _collect_items(
    directory: Path,
    exclude: set[str],
    exclude_hidden: bool,
    sort_mode: str,
    reverse: bool,
) -> list[Path]:
    """Return sorted PDFs and subdirectories (that contain PDFs) in *directory*."""
    items: list[Path] = []
    try:
        for entry in directory.iterdir():
            if exclude_hidden and entry.name.startswith("."):
                continue
            if entry.name in exclude:
                continue
            if entry.is_file() and entry.suffix.lower() == ".pdf":
                items.append(entry)
            elif entry.is_dir() and _dir_has_pdfs(entry, exclude, exclude_hidden):
                items.append(entry)
    except PermissionError as exc:
        logger.warning("Cannot read directory %s: %s", directory, exc)
    return sort_paths(items, mode=sort_mode, reverse=reverse)


def _render_tree(
    directory: Path,
    exclude: set[str],
    exclude_hidden: bool,
    sort_mode: str,
    reverse: bool,
    prefix: str = "",
    is_root: bool = True,
) -> list[str]:
    """Render the merge plan as a tree of strings for dry-run output."""
    lines: list[str] = []
    if is_root:
        lines.append(directory.name)

    items = _collect_items(directory, exclude, exclude_hidden, sort_mode, reverse)
    for i, item in enumerate(items):
        is_last = i == len(items) - 1
        connector = "└── " if is_last else "├── "
        lines.append(f"{prefix}{connector}{item.name}")
        if item.is_dir():
            child_prefix = prefix + ("    " if is_last else "│   ")
            lines.extend(
                _render_tree(
                    item,
                    exclude,
                    exclude_hidden,
                    sort_mode,
                    reverse,
                    child_prefix,
                    is_root=False,
                )
            )
    return lines


def _add_pdf(
    path: Path,
    writer: PdfWriter,
    bookmarks_list: list[Bookmark],
    parent_bookmark: Bookmark | None,
    page_count: list[int],
    strict: bool,
    verbose: bool,
) -> None:
    """Append a single PDF file to *writer* and record its bookmark."""
    if verbose:
        logger.debug("  Adding: %s", path)
    try:
        with open(path, "rb") as fh:
            reader = PdfReader(fh)
            if reader.is_encrypted:
                raise EncryptedPDFError(f"PDF is encrypted: {path}")
            start_page = page_count[0]
            n_pages = len(reader.pages)
            writer.append(reader)
            page_count[0] += n_pages

        bm = Bookmark(start_page, path.stem)
        if parent_bookmark is None:
            bookmarks_list.append(bm)
        else:
            parent_bookmark.add_child(bm)

    except MergeError:
        if strict:
            raise
        logger.warning("Skipping %s: encrypted PDF", path)
    except (PdfReadError, Exception) as exc:  # noqa: BLE001
        if strict:
            raise MergeError(f"Failed to process {path}: {exc}") from exc
        logger.warning("Skipping %s: %s", path, exc)


def _merge_directory(
    directory: Path,
    writer: PdfWriter,
    bookmarks_list: list[Bookmark],
    parent_bookmark: Bookmark | None,
    page_count: list[int],
    exclude: set[str],
    exclude_hidden: bool,
    sort_mode: str,
    reverse: bool,
    strict: bool,
    verbose: bool,
) -> None:
    """Recursively merge PDFs from *directory* into *writer*."""
    items = _collect_items(directory, exclude, exclude_hidden, sort_mode, reverse)

    for item in items:
        if item.is_file():
            _add_pdf(
                item,
                writer,
                bookmarks_list,
                parent_bookmark,
                page_count,
                strict,
                verbose,
            )
        elif item.is_dir():
            if verbose:
                logger.debug("Scanning: %s", item)
            start_page = page_count[0]
            bm = Bookmark(start_page, item.name)
            if parent_bookmark is None:
                bookmarks_list.append(bm)
            else:
                parent_bookmark.add_child(bm)
            _merge_directory(
                item,
                writer,
                bookmarks_list,
                bm,
                page_count,
                exclude,
                exclude_hidden,
                sort_mode,
                reverse,
                strict,
                verbose,
            )


def _write_bookmarks(
    writer: PdfWriter,
    bookmarks: list[Bookmark],
    parent=None,
) -> None:
    """Recursively add bookmarks to the PDF writer's outline."""
    for bm in bookmarks:
        item = writer.add_outline_item(bm.title, bm.page, parent=parent)
        if bm.children:
            _write_bookmarks(writer, bm.children, parent=item)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def merge_pdf_tree(
    input_dir: str | Path,
    output_file: str | Path | None = None,
    sort_mode: str = DEFAULT_SORT_MODE,
    reverse: bool = False,
    exclude: list[str] | None = None,
    bookmarks: bool = True,
    exclude_hidden: bool = DEFAULT_EXCLUDE_HIDDEN,
    dry_run: bool = False,
    strict: bool = False,
    verbose: bool = False,
    quiet: bool = False,
) -> None:
    """Merge all PDFs in a directory tree into a single PDF file.

    Args:
        input_dir: Root directory to scan for PDFs.
        output_file: Destination path for the merged PDF. Defaults to
            ``<input_dir>.pdf`` when *output_file* is None.
        sort_mode: How to order items — ``'natural'``, ``'alpha'``, or
            ``'mtime'``.
        reverse: Reverse the sort order.
        exclude: Directory names to skip entirely.
        bookmarks: Add hierarchical bookmarks to the output PDF.
        exclude_hidden: Skip directories whose names start with ``'.'``.
        dry_run: Print the merge plan without writing any file.
        strict: Raise :class:`~nestedpdfmerger.errors.MergeError` on the
            first problematic PDF instead of skipping it.
        verbose: Emit detailed progress to the logger.
        quiet: Suppress all non-error log output.
    """
    input_dir = Path(input_dir)
    exclude_set: set[str] = set(exclude) if exclude else set()

    if not input_dir.is_dir():
        raise ValueError(f"Input path is not a directory: {input_dir}")

    if dry_run:
        lines = _render_tree(
            input_dir, exclude_set, exclude_hidden, sort_mode, reverse
        )
        print("\n".join(lines))
        return

    if output_file is None:
        output_file = input_dir.with_suffix(".pdf")
    output_file = Path(output_file)

    if not quiet:
        logger.info("Scanning: %s", input_dir)

    writer = PdfWriter()
    bookmarks_list: list[Bookmark] = []
    page_count = [0]

    _merge_directory(
        input_dir,
        writer,
        bookmarks_list,
        None,
        page_count,
        exclude_set,
        exclude_hidden,
        sort_mode,
        reverse,
        strict,
        verbose and not quiet,
    )

    if bookmarks:
        _write_bookmarks(writer, bookmarks_list)

    if not quiet:
        logger.info("Writing: %s (%d pages)", output_file, page_count[0])

    with open(output_file, "wb") as fh:
        writer.write(fh)

    if not quiet:
        logger.info("Done.")
