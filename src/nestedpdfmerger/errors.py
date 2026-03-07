"""Custom exceptions for nestedpdfmerger."""


class MergeError(Exception):
    """Raised in strict mode when a PDF cannot be processed."""


class EncryptedPDFError(MergeError):
    """Raised when a PDF file is encrypted and cannot be merged."""


class CorruptedPDFError(MergeError):
    """Raised when a PDF file is corrupted and cannot be read."""
