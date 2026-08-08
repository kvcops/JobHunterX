"""
Unit tests for Search Provider Adapters and Cost Models.
"""

import pytest
from jobhunterx.tools.search_providers import (
    BraveProvider,
    CostStatus,
    DDGSProvider,
    ExaProvider,
    TavilyProvider,
    TinyFishProvider,
    TransportVerdict,
)


def test_tinyfish_provider_availability_and_cost():
    p = TinyFishProvider()
    assert p.name == "tinyfish"
    assert p.is_available({"TINYFISH_API_KEY": ""}) is False
    assert p.is_available({"TINYFISH_API_KEY": "tf_12345"}) is True
    assert p.is_available({"TINYFISH_API_KEY": "tf_12345"}, session_disabled=True) is False

    cost = p.calculate_worst_case_cost({"query": "python developer"})
    assert cost.status == CostStatus.KNOWN
    assert cost.estimated_amount_native == 0.0
    assert cost.unit_type == "credits"


def test_tavily_provider_cost_calculation():
    p = TavilyProvider()
    cost_basic = p.calculate_worst_case_cost({"search_depth": "basic", "auto_parameters": False})
    assert cost_basic.status == CostStatus.KNOWN
    assert cost_basic.estimated_amount_native == 1.0

    cost_auto = p.calculate_worst_case_cost({"search_depth": "basic", "auto_parameters": True})
    assert cost_auto.status == CostStatus.UNKNOWN


def test_exa_provider_cost_calculation():
    p = ExaProvider()
    cost_base = p.calculate_worst_case_cost({"numResults": 10})
    assert cost_base.status == CostStatus.KNOWN
    assert cost_base.estimated_amount_native == 0.007

    cost_extra = p.calculate_worst_case_cost({"numResults": 15})
    assert cost_extra.status == CostStatus.KNOWN
    assert cost_extra.estimated_amount_native == 0.012

    cost_unknown = p.calculate_worst_case_cost({"numResults": 10, "contents": True})
    assert cost_unknown.status == CostStatus.UNKNOWN


def test_brave_provider_availability():
    p = BraveProvider()
    assert p.is_available({"BRAVE_ENABLED": False, "BRAVE_API_KEY": "key"}) is False
    assert p.is_available({"BRAVE_ENABLED": True, "BRAVE_API_KEY": "key"}) is True


def test_ddgs_provider_cost():
    p = DDGSProvider()
    cost = p.calculate_worst_case_cost({"query": "python"})
    assert cost.status == CostStatus.NOT_APPLICABLE
