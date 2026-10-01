"""
Unit tests for API key security and privacy controls.
"""

from jobhunterx.api.routes import _mask


def test_mask():
    assert _mask("") == ""
    assert _mask(None) == ""
    assert _mask("12345") == "******"
    assert _mask("sk_test_123456789") == "********6789"
