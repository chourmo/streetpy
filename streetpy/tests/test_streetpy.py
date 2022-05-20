"""
Unit and regression test for the streetpy package.
"""

# Import package, test suite, and other packages as needed
import sys

import pytest

import streetpy


def test_streetpy_imported():
    """Sample test, will always pass so long as import statement worked."""
    assert "streetpy" in sys.modules
