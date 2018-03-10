import pytest

from async2v.application import Application


@pytest.fixture
def app():
    return Application()


