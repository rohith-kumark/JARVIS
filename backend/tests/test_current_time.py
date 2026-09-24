import pytest
from backend.app.tools.builtin.current_time import CurrentTimeTool


@pytest.fixture
def time_tool():
    return CurrentTimeTool()


@pytest.mark.asyncio
async def test_current_time_default_utc(time_tool):
    """Test get_current_time with default UTC timezone."""
    result = await time_tool.execute()
    assert result.success is True
    data = result.data
    assert data["timezone"] == "UTC"
    assert "iso_8601" in data
    assert "formatted" in data
    assert "day_of_week" in data
    assert "unix_timestamp" in data


@pytest.mark.asyncio
async def test_current_time_specific_timezones(time_tool):
    """Test get_current_time with specific IANA timezones and local."""
    for tz in ["America/New_York", "Asia/Tokyo", "Asia/Kolkata", "local"]:
        result = await time_tool.execute(timezone=tz)
        assert result.success is True
        assert "iso_8601" in result.data
        assert "formatted" in result.data


@pytest.mark.asyncio
async def test_current_time_invalid_timezone(time_tool):
    """Test get_current_time gracefully reports invalid timezone names."""
    result = await time_tool.execute(timezone="Invalid/NonExistent_Timezone")
    assert result.success is False
    assert "invalid timezone identifier" in result.error.lower()
