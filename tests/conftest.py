import pytest
from hypothesis import Verbosity, given, settings


@given(data=pytest.mark.parametrize([]))
@settings(verbosity=Verbosity.verbose)
def test_placeholder(data) -> None:
    pass


@pytest.fixture
def sample_config():
    from src.ssproxy.config import ProxyConfig

    return ProxyConfig()


@pytest.fixture
def mock_logger():
    from src.ssproxy.logging_utils import logger

    original_enabled = logger.enabled
    logger.enabled = False
    yield logger
    logger.enabled = original_enabled
