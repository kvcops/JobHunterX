"""Tests for graph.py auto-apply wiring + geo_search.py job-count scaling.

Verifies the plumbing that makes "surface N jobs" work:
- run_full_search() accepts auto_apply and drives it from pipeline mode
- routes.py passes auto_apply through from _pipeline_mode
- geo_search._effective_max_jobs() scales the discovery hard cap
"""

import inspect
from pathlib import Path

import pytest

from vellum.agents import graph, geo_search
from vellum.agents.geo_search import _effective_max_jobs


class TestGraphAutoApply:
    def test_run_full_search_has_auto_apply_param(self):
        sig = inspect.signature(graph.run_full_search)
        assert "auto_apply" in sig.parameters
        assert sig.parameters["auto_apply"].default is False

    def test_max_rounds_eight(self):
        graph_src = Path("vellum/agents/graph.py").read_text(encoding="utf-8")
        assert "MAX_ROUNDS = 8" in graph_src

    def test_apply_semaphore_three(self):
        graph_src = Path("vellum/agents/graph.py").read_text(encoding="utf-8")
        assert "APPLY_SEMAPHORE = 3" in graph_src


class TestRoutesWiring:
    def test_start_search_passes_auto_apply(self):
        """routes.py must forward pipeline mode into run_full_search."""
        routes_src = Path(
            "vellum/api/routes.py"
        ).read_text(encoding="utf-8")
        assert "auto_apply=(_pipeline_mode == \"automatic\")" in routes_src

    def test_pipeline_mode_default_manual(self):
        routes_src = Path(
            "vellum/api/routes.py"
        ).read_text(encoding="utf-8")
        assert "_pipeline_mode: str = \"manual\"" in routes_src


class TestEffectiveMaxJobs:
    def test_small_limit_floor(self):
        assert _effective_max_jobs(5) >= 80

    def test_medium_limit_scales(self):
        assert _effective_max_jobs(25) >= 50
        assert _effective_max_jobs(25) < 600

    def test_hard_cap_600(self):
        assert _effective_max_jobs(1000) == 600

    def test_never_below_80(self):
        assert _effective_max_jobs(1) == 80

    def test_ten_limit_floor(self):
        assert _effective_max_jobs(10) >= 80
