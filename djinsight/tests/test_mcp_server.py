"""Tests for the FastMCP server tool registration."""

import pytest

EXPECTED_TOOLS = [
    "get_page_stats",
    "get_top_pages",
    "list_tracked_models",
    "get_period_stats",
    "compare_periods",
    "get_trending_pages",
    "get_referrer_stats",
    "get_traffic_sources",
    "get_device_breakdown",
    "get_hourly_pattern",
    "get_site_overview",
    "compare_content_types",
    "search_pages",
]


@pytest.mark.django_db
class TestMCPServerRegistration:
    def test_all_tools_registered(self):
        """Verify all 13 tools are registered with the FastMCP server."""
        from djinsight.mcp.server import mcp

        registered = set(mcp._tool_manager._tools.keys())
        assert (
            len(registered) == 13
        ), f"Expected 13 tools, got {len(registered)}: {registered}"

    def test_expected_tool_names(self):
        """Verify each expected tool name is registered."""
        from djinsight.mcp.server import mcp

        registered = set(mcp._tool_manager._tools.keys())
        for tool_name in EXPECTED_TOOLS:
            assert (
                tool_name in registered
            ), f"Tool '{tool_name}' not registered. Registered: {registered}"

    def test_no_extra_tools(self):
        """Verify no unexpected tools are registered."""
        from djinsight.mcp.server import mcp

        registered = set(mcp._tool_manager._tools.keys())
        expected = set(EXPECTED_TOOLS)
        extra = registered - expected
        assert not extra, f"Unexpected tools registered: {extra}"
