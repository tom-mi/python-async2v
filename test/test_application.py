import time

import pytest

from async2v.application import Application
from async2v.components.base import Component
from async2v.fields import Output, Latest


@pytest.fixture
def app():
    return Application()


class SampleSource(Component):
    target_fps = 10

    def __init__(self, data, name='sample'):
        self.output = Output(name)
        self.data = data.copy()

    async def process(self):
        try:
            self.output.push(self.data.pop(0))
        except IndexError:
            self.logger.warning('End of data reached')


class SampleSink(Component):
    target_fps = 10

    def __init__(self, name='sample'):
        self.input = Latest(name)
        self.data = []

    async def process(self):
        if self.input.updated:
            self.data.append(self.input.value)


class SquareFilter(Component):
    target_fps = 10

    def __init__(self, input_, output):
        self.input = Latest(input_)
        self.output = Output(output)

    async def process(self):
        if self.input.updated:
            self.output.push(self.input.value ** 2)


def test_source_to_sink(app):
    data = [1, 2, 3]
    source = SampleSource(data=data)
    sink = SampleSink()
    app.register(sink)
    app.register(source)
    app.start()
    time.sleep(1)
    app.stop()

    assert sink.data == data


def test_source_to_filter_to_sink(app):
    data = [1, 2, 3]
    source = SampleSource(data, name='src')
    square_filter = SquareFilter('src', 'dst')
    sink = SampleSink(name='dst')
    app.register(sink)
    app.register(square_filter)
    app.register(source)
    app.start()
    time.sleep(1)
    app.stop()

    assert sink.data == [d * d for d in data]
