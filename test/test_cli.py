from pathlib import Path

import cv2
import pytest

from async2v.application import Application
from async2v.cli import ApplicationLauncher
from async2v.components.base import EventDrivenComponent
from async2v.components.opencv.video import SimpleDisplaySink, Frame, VideoSource
from async2v.components.pygame.display import OpenCvDisplay
from async2v.components.pygame.main import MainWindow
from async2v.fields import Latest, Output


class FlipFilter(EventDrivenComponent):

    def __init__(self, in_key, out_key):
        self.input: Latest[Frame] = Latest(in_key, trigger=True)
        self.output: Output[Frame] = Output(out_key)

    async def process(self) -> None:
        flipped = cv2.flip(self.input.value.image, 0)
        self.output.push(Frame(flipped, 'flipped'))


class SimpleLauncher(ApplicationLauncher):

    def __init__(self):
        super().__init__()
        self.add_configurator(VideoSource.configurator())

    def register_application_components(self, args, app: Application):
        source = VideoSource(VideoSource.configurator().config_from_args(args))
        app.register(source)
        app.register(FlipFilter('source', 'flipped'))
        app.register(SimpleDisplaySink('flipped'))


class PygameLauncher(ApplicationLauncher):

    def __init__(self):
        super().__init__()
        self.add_configurator(VideoSource.configurator())
        self.add_configurator(MainWindow.configurator())

    def register_application_components(self, args, app: Application):
        source = VideoSource(VideoSource.configurator().config_from_args(args))
        displays = [
            OpenCvDisplay('flipped')
        ]
        app.register(source)
        app.register(FlipFilter('source', 'flipped'))
        app.register(MainWindow(displays=displays, config=MainWindow.configurator().config_from_args(args)))


@pytest.fixture
def simple_launcher(configure_logging):
    return SimpleLauncher()


@pytest.fixture
def pygame_launcher(configure_logging):
    return PygameLauncher()


def test_graph(tmp_path: Path, simple_launcher, video_file):
    graph_path = tmp_path / 'graph'
    pdf_path = tmp_path / 'graph.pdf'
    # We need a source file here, as in the CI environment there is no camera
    simple_launcher.main(['graph', '--output', str(graph_path), '--source-file', video_file])

    assert graph_path.exists()
    assert graph_path.open().read().startswith('digraph')
    assert pdf_path.exists()
    assert pdf_path.open('rb').read().startswith(b'%PDF-')


def test_run(simple_launcher, video_file):
    simple_launcher.main(['run', '--source-file', video_file])


def test_pygame_graph(tmp_path: Path, pygame_launcher, video_file):
    graph_path = tmp_path / 'graph'
    pdf_path = tmp_path / 'graph.pdf'
    # We need a source file here, as in the CI environment there is no camera
    pygame_launcher.main(['graph', '--output', str(graph_path), '--source-file', video_file])

    assert graph_path.exists()
    assert graph_path.open().read().startswith('digraph')
    assert pdf_path.exists()
    assert pdf_path.open('rb').read().startswith(b'%PDF-')


def test_pygame_run(pygame_launcher, video_file):
    pygame_launcher.main(['run', '--source-file', video_file])


def test_pygame_list_resolutions(pygame_launcher, video_file, capsys):
    pygame_launcher.main(['list-resolutions'])

    captured = capsys.readouterr()
    assert '640x480' in captured.out
