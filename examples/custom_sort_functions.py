"""
Domain-specific sort functions from the original internal script.

These are preserved here as reference examples showing how to supply a
custom sort key via the nestedpdfmerger Python API. They are NOT part of
the main package and must not be imported by the library itself.

Usage example
-------------
    from nestedpdfmerger.merger import _merge_directory  # internal
    # or build your own pipeline using the public API

    from nestedpdfmerger import merge_pdf_tree
    from examples.custom_sort_functions import sf_top_down_reports

    # The public API currently supports the three built-in sort modes
    # ('natural', 'alpha', 'mtime'). Custom sort functions can be used
    # by calling the internal helpers directly if you need this level
    # of control (note: internal APIs may change between releases).
"""

from __future__ import annotations

import os


def example_sort_func(val: str) -> float:
    """
    Files are ordered by company then by report type.

    A very naive example :)
    """
    val = os.path.basename(val)

    if val.partition(".")[0].isnumeric():
        return int(val.partition(".")[0])

    comp_val = 0.0
    rpt_val = 0.0

    companies: dict[str, float] = {
        "AAA": 100.0,
        "BBB": 101.0,
        "CCC": 102.0,
    }

    reports: dict[str, float] = {
        "Alpha.pdf": 0.1,
        "Bravo.pdf": 0.2,
        "Charlie.pdf": 0.25,
    }

    for key, value in companies.items():
        if val.startswith(key):
            comp_val = value
    for key, value in reports.items():
        if val.endswith(key):
            rpt_val = value

    return comp_val + rpt_val
