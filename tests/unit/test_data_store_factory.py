import pytest

from rada.data.storage import InMemoryDecisionStore, SQLiteDecisionStore
from rada.data.timescale_store import TimescaleDecisionStore
from rada.main import RuntimeSettings, build_data_store


@pytest.mark.unit
def test_build_data_store_sqlite_mode() -> None:
    settings = RuntimeSettings(data_store_mode="sqlite", sqlite_url="sqlite:///./tmp.db")

    store = build_data_store(settings)

    assert isinstance(store, SQLiteDecisionStore)


@pytest.mark.unit
def test_build_data_store_timescale_mode() -> None:
    settings = RuntimeSettings(
        data_store_mode="timescale",
        database_url="postgresql://rada:rada@localhost:5432/rada",
    )

    store = build_data_store(settings)

    assert isinstance(store, TimescaleDecisionStore)


@pytest.mark.unit
def test_build_data_store_inmemory_mode() -> None:
    settings = RuntimeSettings(data_store_mode="inmemory")

    store = build_data_store(settings)

    assert isinstance(store, InMemoryDecisionStore)


@pytest.mark.unit
def test_build_data_store_invalid_mode_raises() -> None:
    settings = RuntimeSettings(data_store_mode="unknown")

    with pytest.raises(ValueError, match="Unsupported RADA_DATA_STORE_MODE"):
        build_data_store(settings)
