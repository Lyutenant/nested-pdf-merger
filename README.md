# nestedpdfmerger

Merge PDFs recursively from a folder tree into a single PDF with automatic hierarchical bookmarks based on the directory structure.

## Installation

```bash
pip install nestedpdfmerger
```

## Quick start

```bash
nestedpdfmerger ./reports -o merged.pdf
```

## Example input tree

```
reports/
├── intro.pdf
├── chapter1/
│   ├── part1.pdf
│   └── part2.pdf
└── appendix/
    └── appendixA.pdf
```

Resulting bookmarks in `merged.pdf`:

```
intro
chapter1
 ├─ part1
 └─ part2
appendix
 └─ appendixA
```

## Usage

```
nestedpdfmerger INPUT_DIR -o OUTPUT.pdf [options]
```

### Options

| Flag | Description |
|---|---|
| `-o, --output PATH` | Output PDF path (default: `<INPUT_DIR>.pdf`) |
| `--sort {natural,alpha,mtime}` | Sort mode (default: `natural`) |
| `--reverse` | Reverse sort order |
| `--exclude NAME [NAME ...]` | Directory names to skip |
| `--exclude-hidden` | Skip hidden directories (starting with `.`) |
| `--no-bookmarks` | Disable hierarchical bookmarks |
| `--dry-run` | Preview merge order without writing output |
| `--strict` | Stop on first PDF error instead of skipping |
| `--verbose` | Show detailed progress |
| `--quiet` | Suppress non-error output |
| `--version` | Show version and exit |

### Examples

Preview what would be merged:

```bash
nestedpdfmerger ./reports --dry-run
```

Natural sort, exclude backup folders, verbose output:

```bash
nestedpdfmerger ./reports \
  --output merged.pdf \
  --sort natural \
  --exclude Backup Data \
  --verbose
```

Sort by modification time, newest last:

```bash
nestedpdfmerger ./reports -o merged.pdf --sort mtime --reverse
```

## Python API

```python
from nestedpdfmerger import merge_pdf_tree

merge_pdf_tree(
    input_dir="reports",
    output_file="merged.pdf",
    sort_mode="natural",
    exclude=["Backup", "Data"],
    bookmarks=True,
)
```

## Sort modes

| Mode | Description |
|---|---|
| `natural` | Human-friendly natural sort (1, 2, 10 not 1, 10, 2) |
| `alpha` | Case-insensitive alphabetical |
| `mtime` | File/directory modification time (oldest first) |

## Error handling

By default, corrupted, encrypted, or unreadable PDFs are **warned and skipped**. Use `--strict` to stop on the first error.

## License

MIT
