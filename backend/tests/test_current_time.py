"""Tests for the current time tool."""

from backend.app.tools.builtin.current_time import CurrentTimeTool


def test_current_time_output_structure():
    tool = CurrentTimeTool()
    res = tool.execute()

    assert "iso_local" in res
    assert "iso_utc" in res
    assert "formatted_local" in res
    assert "formatted_utc" in res
    assert "year" in res
    assert "day_of_week" in res
    assert isinstance(res["year"], int)
    assert res["year"] >= 2024
