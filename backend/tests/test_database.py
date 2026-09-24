import pytest
from backend.app.core.config import Settings
from backend.app.db.base import Base, TimestampMixin
from backend.app.db.session import check_db_health, get_async_engine
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String


class DummyEntity(Base, TimestampMixin):
    __tablename__ = "dummy_entity"
    id: Mapped[str] = mapped_column(String, primary_key=True)


def test_database_url_formatting():
    settings = Settings(
        POSTGRES_SERVER="db.internal",
        POSTGRES_PORT=5432,
        POSTGRES_USER="jarvis_user",
        POSTGRES_PASSWORD="secure_password",
        POSTGRES_DB="jarvis_prod",
    )
    assert settings.async_database_url == "postgresql+asyncpg://jarvis_user:secure_password@db.internal:5432/jarvis_prod"


def test_database_url_override():
    settings = Settings(
        DATABASE_URL="postgresql://user:pass@remote:5433/custom_db"
    )
    assert settings.async_database_url == "postgresql+asyncpg://user:pass@remote:5433/custom_db"


def test_orm_base_and_mixin():
    entity = DummyEntity(id="test-123")
    assert entity.id == "test-123"
    assert "dummy_entity" in Base.metadata.tables


@pytest.mark.asyncio
async def test_db_health_probe_structure():
    health = await check_db_health()
    assert isinstance(health, dict)
    assert "status" in health
    assert "engine" in health
    assert health["engine"] == "postgresql+asyncpg"
