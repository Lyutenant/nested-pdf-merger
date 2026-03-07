"""nestedpdfmerger — merge PDFs recursively with hierarchical bookmarks."""

from .merger import merge_pdf_tree

__version__ = "1.0.0"
__all__ = ["merge_pdf_tree", "__version__"]
