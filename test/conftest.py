import os.path

import logwood
import pytest
from logwood.handlers.stderr import ColoredStderrHandler

from async2v.application import Application


@pytest.fixture(autouse=True)
def configure_logging():
    logwood.basic_config(
        level=logwood.DEBUG,
        handlers=[ColoredStderrHandler()],
        format='%(timestamp).6f %(level)-5s %(name)s: %(message)s',
    )


@pytest.fixture
def app(configure_logging) -> Application:
    return Application()


@pytest.fixture
def video_file():
    return os.path.join(os.path.dirname(__file__), 'data', 'video.mp4')


@pytest.fixture
def video_source(video_file):
    from async2v.components.opencv.video import VideoSource, VideoSourceConfig
    source_config = VideoSourceConfig(path=video_file, fps=200)  # Pass a high frame rate to speed up test
    return VideoSource(source_config, key='source')
