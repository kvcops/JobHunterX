import pytest


@pytest.fixture(autouse=True)
def temp_db():
    """Browser tests talk to a separate server process with its own database."""
    yield None
