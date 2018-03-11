import time

from async2v.components.base import BareComponent, EventDrivenComponent
from async2v.fields import Output, Buffer


def test_register_during_runtime(app):
    source = SampleSource()
    sink1 = SampleSink()
    sink2 = SampleSink()
    app.register(source, sink1)
    app.start()
    time.sleep(0.1)
    source.push('1')
    app.register(sink2)
    source.push('2')
    time.sleep(0.2)
    app.stop()

    assert sink1.log == ['setup', '1', '2', 'cleanup']
    assert sink2.log == ['setup', '2', 'cleanup']


def test_deregister_during_runtime(app):
    source = SampleSource()
    sink1 = SampleSink()
    sink2 = SampleSink()
    app.register(source, sink1, sink2)
    app.start()
    time.sleep(0.1)
    source.push('1')
    app.deregister(sink2)
    source.push('2')
    time.sleep(0.2)
    app.stop()

    assert sink1.log == ['setup', '1', '2', 'cleanup']
    assert sink2.log == ['setup', '1', 'cleanup']


class SampleSink(EventDrivenComponent):
    def __init__(self, name='sample'):
        self.input = Buffer(name, trigger=True)
        self.log = []

    async def setup(self):
        self.log.append('setup')

    async def process(self):
        self.log += self.input.values

    async def cleanup(self):
        self.log.append('cleanup')


class SampleSource(BareComponent):

    def __init__(self):
        self.output = Output('sample')

    def push(self, value):
        self.output.push(value)
