import time

from async2v.application._graph import ApplicationGraph
from async2v.components.base import EventDrivenComponent, BareComponent
from async2v.fields import Output, Buffer, Latest


def test_branching_scenario(app):
    item_source = ItemSource()
    label_source = LabelSource()
    sink = ItemSink()
    app.register(sink)
    app.register(item_source)
    app.register(Labeler())
    app.register(label_source)
    app.start()
    label_source.push_label('A')
    item_source.push_item('car')
    item_source.push_item('boat')
    item_source.push_item('bike')
    time.sleep(0.1)
    label_source.push_label('B')
    item_source.push_item('shoes')
    app.stop()

    assert sink.data == ['carA', 'boatA', 'bikeA', 'shoesB']


def test_graph(app):
    item_source = ItemSource()
    label_source = LabelSource()
    sink = ItemSink()
    app.register(sink)
    app.register(item_source)
    app.register(Labeler())
    app.register(label_source)

    graph = ApplicationGraph(app._registry)
    source = graph.source()

    # Only smoke test that graphing compiles and returns a probably valid graph
    assert source.startswith('digraph {')
    assert source.endswith('}')


class ItemSource(BareComponent):

    def __init__(self):
        self.output = Output('item_source')

    def push_item(self, item):
        self.output.push(item)


class LabelSource(BareComponent):

    def __init__(self):
        self.output = Output('label')

    def push_label(self, label: str):
        self.output.push(label)


class Labeler(EventDrivenComponent):

    def __init__(self):
        self.item_source = Buffer('item_source', trigger=True)
        self.label = Latest('label')
        self.output = Output('sink')

    async def process(self):
        for item in self.item_source.values:
            self.output.push(item + self.label.value)


class ItemSink(EventDrivenComponent):
    def __init__(self, name='sink'):
        self.input = Buffer(name, trigger=True)
        self.data = []

    async def process(self):
        self.data += self.input.values
