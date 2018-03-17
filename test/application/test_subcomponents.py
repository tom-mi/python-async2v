from async2v.components.base import BareComponent, EventDrivenComponent, ContainerMixin, SubComponent
from async2v.fields import Output, Buffer


def test_sub_component(app):
    source = EventSource()
    sub_component = SampleSubComponent()
    other_sub_component = SampleSubComponent()
    component = SampleComponent([sub_component, other_sub_component])

    app.register(source, component)
    app.start()
    source.push('1')
    source.push('2')
    sub_component.push('3')
    app.stop()

    assert sub_component.log == ['1', '2', '3']
    assert other_sub_component.log == ['1', '2', '3']


class SampleSubComponent(SubComponent):

    def __init__(self):
        self.input = Buffer('sample', trigger=True)
        self.output = Output('sample')
        self.log = []

    def push(self, value):
        self.output.push(value)

    def do_something(self):
        self.log += self.input.values


class SampleComponent(EventDrivenComponent, ContainerMixin):

    def __init__(self, sub_components):
        super().__init__(sub_components)
        self._sub_components = sub_components

    async def process(self):
        for sub_component in self._sub_components:
            sub_component.do_something()


class EventSource(BareComponent):

    def __init__(self):
        self.output = Output('sample')

    def push(self, value):
        self.output.push(value)
