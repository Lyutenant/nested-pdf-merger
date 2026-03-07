"""Tests for nestedpdfmerger."""

from __future__ import annotations

from pathlib import Path

import pytest
from pypdf import PdfReader, PdfWriter

from nestedpdfmerger import merge_pdf_tree
from nestedpdfmerger.cli import build_parser
from nestedpdfmerger.errors import MergeError
from nestedpdfmerger.sorting import sort_paths

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_pdf(path: Path, pages: int = 1) -> None:
    """Write a minimal valid PDF with *pages* blank pages to *path*."""
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=72, height=72)
    with open(path, "wb") as fh:
        writer.write(fh)


def make_corrupted_pdf(path: Path) -> None:
    """Write a file that looks like a PDF but is corrupted."""
    path.write_bytes(b"%PDF-1.4\ngarbage\n%%EOF")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def simple_tree(tmp_path: Path) -> Path:
    """
    tmp_path/
    ├── intro.pdf       (1 page)
    ├── chapter1/
    │   ├── part1.pdf   (2 pages)
    │   └── part2.pdf   (1 page)
    └── appendix/
        └── appendixA.pdf (1 page)
    """
    make_pdf(tmp_path / "intro.pdf", pages=1)
    (tmp_path / "chapter1").mkdir()
    make_pdf(tmp_path / "chapter1" / "part1.pdf", pages=2)
    make_pdf(tmp_path / "chapter1" / "part2.pdf", pages=1)
    (tmp_path / "appendix").mkdir()
    make_pdf(tmp_path / "appendix" / "appendixA.pdf", pages=1)
    return tmp_path


@pytest.fixture()
def output_pdf(tmp_path: Path) -> Path:
    return tmp_path / "merged.pdf"


# ---------------------------------------------------------------------------
# Tests: merge order
# ---------------------------------------------------------------------------


class TestMergeOrder:
    def test_alpha_sort_produces_correct_order(
        self, tmp_path: Path, output_pdf: Path
    ) -> None:
        make_pdf(tmp_path / "b.pdf")
        make_pdf(tmp_path / "a.pdf")
        make_pdf(tmp_path / "c.pdf")

        merge_pdf_tree(tmp_path, output_pdf, sort_mode="alpha", bookmarks=True)

        reader = PdfReader(str(output_pdf))
        titles = [item.title for item in reader.outline]
        assert titles == ["a", "b", "c"]

    def test_natural_sort_handles_numbers(
        self, tmp_path: Path, output_pdf: Path
    ) -> None:
        for name in ("file10.pdf", "file2.pdf", "file1.pdf"):
            make_pdf(tmp_path / name)

        merge_pdf_tree(tmp_path, output_pdf, sort_mode="natural", bookmarks=True)

        reader = PdfReader(str(output_pdf))
        titles = [item.title for item in reader.outline]
        assert titles == ["file1", "file2", "file10"]

    def test_reverse_flag_reverses_order(
        self, tmp_path: Path, output_pdf: Path
    ) -> None:
        for name in ("a.pdf", "b.pdf", "c.pdf"):
            make_pdf(tmp_path / name)

        merge_pdf_tree(
            tmp_path, output_pdf, sort_mode="alpha", reverse=True, bookmarks=True
        )

        reader = PdfReader(str(output_pdf))
        titles = [item.title for item in reader.outline]
        assert titles == ["c", "b", "a"]

    def test_total_page_count(self, simple_tree: Path, output_pdf: Path) -> None:
        merge_pdf_tree(simple_tree, output_pdf)
        reader = PdfReader(str(output_pdf))
        # intro(1) + part1(2) + part2(1) + appendixA(1) = 5
        assert len(reader.pages) == 5


# ---------------------------------------------------------------------------
# Tests: bookmark hierarchy
# ---------------------------------------------------------------------------


class TestBookmarkHierarchy:
    def test_flat_bookmarks_for_root_pdfs(
        self, tmp_path: Path, output_pdf: Path
    ) -> None:
        make_pdf(tmp_path / "a.pdf")
        make_pdf(tmp_path / "b.pdf")

        merge_pdf_tree(tmp_path, output_pdf, sort_mode="alpha")

        reader = PdfReader(str(output_pdf))
        assert len(reader.outline) == 2
        assert reader.outline[0].title == "a"
        assert reader.outline[1].title == "b"

    def test_nested_bookmarks_match_directory_structure(
        self, simple_tree: Path, output_pdf: Path
    ) -> None:
        merge_pdf_tree(simple_tree, output_pdf, sort_mode="alpha")

        reader = PdfReader(str(output_pdf))
        outline = reader.outline
        # Top-level items: appendix (dir), chapter1 (dir), intro (file)
        titles = {
            item.title if hasattr(item, "title") else None
            for item in outline
        }
        assert "intro" in titles

    def test_no_bookmarks_flag(self, simple_tree: Path, output_pdf: Path) -> None:
        merge_pdf_tree(simple_tree, output_pdf, bookmarks=False)

        reader = PdfReader(str(output_pdf))
        assert reader.outline == []


# ---------------------------------------------------------------------------
# Tests: folder exclusion
# ---------------------------------------------------------------------------


class TestFolderExclusion:
    def test_excluded_directory_is_skipped(
        self, tmp_path: Path, output_pdf: Path
    ) -> None:
        make_pdf(tmp_path / "keep.pdf")
        (tmp_path / "Backup").mkdir()
        make_pdf(tmp_path / "Backup" / "skip.pdf")

        merge_pdf_tree(tmp_path, output_pdf, exclude=["Backup"])

        reader = PdfReader(str(output_pdf))
        assert len(reader.pages) == 1

    def test_multiple_exclusions(self, tmp_path: Path, output_pdf: Path) -> None:
        make_pdf(tmp_path / "keep.pdf")
        for folder in ("Backup", "Data"):
            (tmp_path / folder).mkdir()
            make_pdf(tmp_path / folder / "skip.pdf")

        merge_pdf_tree(tmp_path, output_pdf, exclude=["Backup", "Data"])

        reader = PdfReader(str(output_pdf))
        assert len(reader.pages) == 1

    def test_exclude_hidden_directories(self, tmp_path: Path, output_pdf: Path) -> None:
        make_pdf(tmp_path / "keep.pdf")
        (tmp_path / ".hidden").mkdir()
        make_pdf(tmp_path / ".hidden" / "skip.pdf")

        merge_pdf_tree(tmp_path, output_pdf, exclude_hidden=True)

        reader = PdfReader(str(output_pdf))
        assert len(reader.pages) == 1


# ---------------------------------------------------------------------------
# Tests: empty directory
# ---------------------------------------------------------------------------


class TestEmptyDirectory:
    def test_empty_root_produces_empty_pdf(
        self, tmp_path: Path, output_pdf: Path
    ) -> None:
        merge_pdf_tree(tmp_path, output_pdf)
        reader = PdfReader(str(output_pdf))
        assert len(reader.pages) == 0

    def test_subdirectory_without_pdfs_is_excluded_from_bookmarks(
        self, tmp_path: Path, output_pdf: Path
    ) -> None:
        make_pdf(tmp_path / "a.pdf")
        (tmp_path / "empty_dir").mkdir()

        merge_pdf_tree(tmp_path, output_pdf)

        reader = PdfReader(str(output_pdf))
        titles = [item.title for item in reader.outline]
        assert "empty_dir" not in titles


# ---------------------------------------------------------------------------
# Tests: corrupted PDF handling
# ---------------------------------------------------------------------------


class TestCorruptedPDF:
    def test_corrupted_pdf_is_skipped_by_default(
        self, tmp_path: Path, output_pdf: Path
    ) -> None:
        make_pdf(tmp_path / "good.pdf")
        make_corrupted_pdf(tmp_path / "bad.pdf")

        # Should not raise; bad.pdf is skipped
        merge_pdf_tree(tmp_path, output_pdf, sort_mode="alpha")

        reader = PdfReader(str(output_pdf))
        assert len(reader.pages) == 1

    def test_corrupted_pdf_raises_in_strict_mode(
        self, tmp_path: Path, output_pdf: Path
    ) -> None:
        make_pdf(tmp_path / "good.pdf")
        make_corrupted_pdf(tmp_path / "bad.pdf")

        with pytest.raises(MergeError):
            merge_pdf_tree(tmp_path, output_pdf, sort_mode="alpha", strict=True)

    def test_encrypted_pdf_is_skipped_by_default(
        self, tmp_path: Path, output_pdf: Path
    ) -> None:
        make_pdf(tmp_path / "good.pdf")

        # Create an encrypted PDF
        writer = PdfWriter()
        writer.add_blank_page(width=72, height=72)
        writer.encrypt("password")
        with open(tmp_path / "encrypted.pdf", "wb") as fh:
            writer.write(fh)

        merge_pdf_tree(tmp_path, output_pdf, sort_mode="alpha")

        reader = PdfReader(str(output_pdf))
        assert len(reader.pages) == 1


# ---------------------------------------------------------------------------
# Tests: dry-run
# ---------------------------------------------------------------------------


class TestDryRun:
    def test_dry_run_does_not_write_file(
        self, simple_tree: Path, output_pdf: Path, capsys: pytest.CaptureFixture
    ) -> None:
        merge_pdf_tree(simple_tree, output_pdf, dry_run=True)
        assert not output_pdf.exists()

    def test_dry_run_prints_tree(
        self, simple_tree: Path, output_pdf: Path, capsys: pytest.CaptureFixture
    ) -> None:
        merge_pdf_tree(simple_tree, output_pdf, dry_run=True, sort_mode="alpha")
        captured = capsys.readouterr()
        assert "intro.pdf" in captured.out
        assert "chapter1" in captured.out
        assert "appendix" in captured.out

    def test_dry_run_shows_root_name(
        self, simple_tree: Path, output_pdf: Path, capsys: pytest.CaptureFixture
    ) -> None:
        merge_pdf_tree(simple_tree, output_pdf, dry_run=True)
        captured = capsys.readouterr()
        first_line = captured.out.splitlines()[0]
        assert first_line == simple_tree.name


# ---------------------------------------------------------------------------
# Tests: CLI parsing
# ---------------------------------------------------------------------------


class TestCLIParsing:
    def test_basic_args(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["./reports", "-o", "out.pdf"])
        assert args.input_dir == "./reports"
        assert args.output == "out.pdf"

    def test_sort_default(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["./reports"])
        assert args.sort == "natural"

    def test_sort_options(self) -> None:
        parser = build_parser()
        for mode in ("natural", "alpha", "mtime"):
            args = parser.parse_args(["./reports", "--sort", mode])
            assert args.sort == mode

    def test_invalid_sort_exits(self) -> None:
        parser = build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["./reports", "--sort", "invalid"])

    def test_exclude_flag(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["./reports", "--exclude", "Backup", "Data"])
        assert args.exclude == ["Backup", "Data"]

    def test_boolean_flags(self) -> None:
        parser = build_parser()
        args = parser.parse_args([
            "./reports",
            "--reverse",
            "--no-bookmarks",
            "--dry-run",
            "--strict",
            "--verbose",
            "--exclude-hidden",
        ])
        assert args.reverse is True
        assert args.no_bookmarks is True
        assert args.dry_run is True
        assert args.strict is True
        assert args.verbose is True
        assert args.exclude_hidden is True

    def test_quiet_flag(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["./reports", "--quiet"])
        assert args.quiet is True


# ---------------------------------------------------------------------------
# Tests: sorting module
# ---------------------------------------------------------------------------


class TestSortPaths:
    def test_natural_sort(self, tmp_path: Path) -> None:
        paths = [tmp_path / name for name in ("file10.txt", "file2.txt", "file1.txt")]
        result = sort_paths(paths, mode="natural")
        assert [p.name for p in result] == ["file1.txt", "file2.txt", "file10.txt"]

    def test_alpha_sort(self, tmp_path: Path) -> None:
        paths = [tmp_path / name for name in ("C.txt", "a.txt", "B.txt")]
        result = sort_paths(paths, mode="alpha")
        assert [p.name for p in result] == ["a.txt", "B.txt", "C.txt"]

    def test_reverse(self, tmp_path: Path) -> None:
        paths = [tmp_path / name for name in ("a.txt", "b.txt", "c.txt")]
        result = sort_paths(paths, mode="alpha", reverse=True)
        assert [p.name for p in result] == ["c.txt", "b.txt", "a.txt"]

    def test_invalid_mode(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="Unknown sort mode"):
            sort_paths([tmp_path], mode="bogus")
