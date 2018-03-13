import time

from async2v.components.base import BareComponent
from async2v.fields import Output, InputQueue


def test_bare_scenario(app):
    source = SampleSource()
    sink = SampleSink()
    app.register(source, sink)
    app.start()
    source.push('1')
    source.push('2')
    time.sleep(0.1)
    app.stop()

    assert sink.log == ['setup', '1', '2', 'cleanup']


class SampleSource(BareComponent):

    def __init__(self):
        self.output = Output('sample')

    def push(self, value):
        self.output.push(value)


class SampleSink(BareComponent):

    def __init__(self):
        self.input = InputQueue('sample')
        self.log = []

    async def setup(self):
        self.log.append('setup')

    async def cleanup(self):
        for item in self.input.queue:
            self.log.append(item.value)
        self.log.append('cleanup')
