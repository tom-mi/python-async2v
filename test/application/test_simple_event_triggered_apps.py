import time

from async2v.components.base import EventDrivenComponent, IteratingComponent
from async2v.fields import Latest, Output


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


class SampleSource(IteratingComponent):
    target_fps = 10

    def __init__(self, data, name='sample'):
        self.output = Output(name)
        self.data = data.copy()

    async def process(self):
        try:
            self.output.push(self.data.pop(0))
        except IndexError:
            self.logger.warning('End of data reached')


class SampleSink(EventDrivenComponent):
    def __init__(self, name='sample'):
        self.input = Latest(name, trigger=True)
        self.data = []

    async def process(self):
        self.data.append(self.input.value)


class SquareFilter(EventDrivenComponent):
    def __init__(self, input_, output):
        self.input = Latest(input_, trigger=True)
        self.output = Output(output)

    async def process(self):
        self.output.push(self.input.value ** 2)
