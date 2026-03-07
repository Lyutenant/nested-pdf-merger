# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-03-07

### Added
- Initial public release as a proper CLI package.
- `nestedpdfmerger` command-line tool with full argument support.
- Python API via `from nestedpdfmerger import merge_pdf_tree`.
- Three built-in sort modes: `natural` (default), `alpha`, `mtime`.
- `--reverse` flag to invert sort order.
- `--exclude` flag to skip named directories.
- `--exclude-hidden` flag to skip hidden directories (names starting with `.`).
- `--no-bookmarks` flag to disable hierarchical PDF bookmarks.
- `--dry-run` mode to preview merge order without writing output.
- `--strict` mode to halt on the first PDF error.
- `--verbose` and `--quiet` logging flags.
- Cross-platform support: Windows, macOS, Linux.
- Packaging via `pyproject.toml` (PEP 517/518).
- GitHub Actions CI across Python 3.10, 3.11, 3.12 on all three platforms.
- Domain-specific sort function examples moved to `examples/`.
