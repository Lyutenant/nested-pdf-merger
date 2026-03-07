"""Command-line interface for nestedpdfmerger."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from . import __version__
from .config import DEFAULT_SORT_MODE, VALID_SORT_MODES
from .errors import MergeError
from .merger import merge_pdf_tree


def _setup_logging(verbose: bool, quiet: bool) -> None:
    if quiet:
        level = logging.ERROR
    elif verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO
    logging.basicConfig(level=level, format="%(message)s")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="nestedpdfmerger",
        description=(
            "Merge PDFs recursively from a folder tree into a single PDF "
            "with automatic hierarchical bookmarks."
        ),
    )
    parser.add_argument(
        "input_dir",
        metavar="INPUT_DIR",
        help="Root directory to scan for PDFs.",
    )
    parser.add_argument(
        "-o",
        "--output",
        metavar="PATH",
        default=None,
        help=(
            "Output PDF file path. "
            "Defaults to <INPUT_DIR>.pdf in the same parent directory."
        ),
    )
    parser.add_argument(
        "--sort",
        choices=list(VALID_SORT_MODES),
        default=DEFAULT_SORT_MODE,
        metavar="{" + ",".join(VALID_SORT_MODES) + "}",
        help="Sort mode for files and directories (default: %(default)s).",
    )
    parser.add_argument(
        "--reverse",
        action="store_true",
        help="Reverse the sort order.",
    )
    parser.add_argument(
        "--exclude",
        nargs="+",
        metavar="NAME",
        default=[],
        help="Directory names to exclude (space-separated).",
    )
    parser.add_argument(
        "--exclude-hidden",
        action="store_true",
        help="Exclude hidden directories (names starting with '.').",
    )
    parser.add_argument(
        "--no-bookmarks",
        action="store_true",
        help="Disable hierarchical bookmarks in the output PDF.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview merge order and bookmark structure without writing output.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Stop on the first PDF error instead of skipping the file.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed progress (scanned folders, detected PDFs, etc.).",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress all non-error output.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    _setup_logging(args.verbose, args.quiet)

    output = args.output
    if output is None and not args.dry_run:
        output = str(Path(args.input_dir).resolve().with_suffix(".pdf"))

    try:
        merge_pdf_tree(
            input_dir=args.input_dir,
            output_file=output,
            sort_mode=args.sort,
            reverse=args.reverse,
            exclude=args.exclude,
            bookmarks=not args.no_bookmarks,
            exclude_hidden=args.exclude_hidden,
            dry_run=args.dry_run,
            strict=args.strict,
            verbose=args.verbose,
            quiet=args.quiet,
        )
    except (MergeError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
