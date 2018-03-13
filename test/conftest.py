import logwood
import pytest
from logwood.handlers.stderr import ColoredStderrHandler


@pytest.fixture(autouse=True)
def configure_logging():
    logwood.basic_config(
        level=logwood.DEBUG,
        handlers=[ColoredStderrHandler()],
        format='%(timestamp).6f %(level)-5s %(name)s: %(message)s',
    )
