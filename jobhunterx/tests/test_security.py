"""
Unit tests for API key security and privacy controls.
"""

import pytest
from jobhunterx.api.routes import _mask_api_key


def test_mask_api_key():
    assert _mask_api_key("") == ""
    assert _mask_api_key(None) == ""
    assert _mask_api_key("12345") == "******"
    assert _mask_api_key("sk_test_123456789") == "********6789"
