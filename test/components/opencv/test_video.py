from typing import List

from async2v.components.base import EventDrivenComponent
from async2v.components.opencv.video import Frame, SimpleDisplaySink
from async2v.fields import Buffer


def test_video_source(app, video_source):
    sink = SampleSink()

    app.register(video_source, sink)
    app.start()
    app.join(20)

    assert not app.is_alive()
    assert not app.has_error_occurred()

    assert len(sink.log) == 150
    assert isinstance(sink.log[0], Frame)
    assert sink.log[0].width == 1280
    assert sink.log[0].height == 720
    assert sink.log[0].channels == 3


def test_simple_sink(app, video_source, highgui_test_skipper):
    sink = SimpleDisplaySink('source')

    app.register(video_source, sink)
    app.start()
    app.join(20)

    assert not app.is_alive()
    assert not app.has_error_occurred()


class SampleSink(EventDrivenComponent):
    def __init__(self, key='source'):
        self.input = Buffer(key, trigger=True)
        self.log: List[Frame] = []

    async def process(self):
        self.log += self.input.values
