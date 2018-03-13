import time

from async2v.components.base import IteratingComponent, BareComponent, EventDrivenComponent
from async2v.fields import Latest, Output


def test_iterating_component_handles_setup_cleanup(app):
    def callback():
        return 'process'

    sample = IteratingSample(callback)
    app.register(sample)
    app.start()
    time.sleep(1)
    app.stop()

    assert sample.log[0] == 'setup'
    assert sample.log[1] == 'process'
    assert sample.log[-2] == 'process'
    assert sample.log[-1] == 'cleanup'


def test_iterating_component_calls_cleanup_in_case_of_error(app):
    def callback():
        raise RuntimeError()

    sample = IteratingSample(callback)
    app.register(sample)
    app.start()
    time.sleep(1)
    app.stop()

    assert sample.log[0] == 'setup'
    assert sample.log[1] == 'cleanup'
    assert len(sample.log) == 2


def test_event_driven_component_handles_setup_cleanup(app):
    def callback():
        return 'process'

    sample = EventDrivenSample(callback)
    source = EventSource()
    app.register(sample, source)
    app.start()
    source.trigger()
    app.stop()

    assert sample.log == ['setup', 'process', 'cleanup']


def test_event_driven_component_calls_cleanup_in_case_of_error(app):
    def callback():
        raise RuntimeError()

    sample = EventDrivenSample(callback)
    source = EventSource()
    app.register(sample, source)
    app.start()
    source.trigger()
    source.trigger()
    app.stop()

    assert sample.log == ['setup', 'cleanup']


class IteratingSample(IteratingComponent):
    target_fps = 10

    def __init__(self, process_callback):
        self.process_callback = process_callback
        self.log = []

    async def setup(self):
        self.log.append('setup')

    async def cleanup(self):
        self.log.append('cleanup')

    async def process(self):
        result = self.process_callback()
        self.log.append(result)


class EventDrivenSample(EventDrivenComponent):

    def __init__(self, process_callback):
        self.input = Latest('sample', trigger=True)
        self.process_callback = process_callback
        self.log = []

    async def setup(self):
        self.log.append('setup')

    async def cleanup(self):
        self.log.append('cleanup')

    async def process(self):
        result = self.process_callback()
        self.log.append(result)


class EventSource(BareComponent):

    def __init__(self):
        self.output = Output('sample')

    def trigger(self):
        self.output.push(None)
