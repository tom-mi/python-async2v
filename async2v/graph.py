import typing
from typing import Dict, List

import graphviz

from async2v.components.base import Component, IteratingComponent
from async2v.fields import InputField, Output, DoubleBufferedField


class ComponentNode(typing.NamedTuple):
    component: Component
    inputs: Dict[str, InputField]
    outputs: Dict[str, Output]
    triggers: List[InputField]

    @property
    def id(self) -> str:
        return self.component.id

    @staticmethod
    def create(component: Component) -> 'ComponentNode':
        inputs = dict((k, f) for k, f in vars(component).items() if isinstance(f, InputField))
        outputs = dict((k, f) for k, f in vars(component).items() if isinstance(f, Output))
        triggers = [f for f in vars(component).values() if isinstance(f, DoubleBufferedField) and f.trigger]
        return ComponentNode(component, inputs, outputs, triggers)


class Link(typing.NamedTuple):
    key: str
    source: str
    source_field: Output
    target: str
    target_field: InputField


class ApplicationGraph:

    def __init__(self):
        self._nodes = {}  # type: Dict[str, ComponentNode]
        # all following fields are re-generated on each state change
        self._inputs_by_key = {}  # type: Dict[str, List[InputField]]
        self._triggered_components_by_key = {}  # type: Dict[str, List[Component]]

    def register(self, component):
        node = ComponentNode.create(component)
        if node.id in self._nodes:
            raise ValueError(f'Component {node.id} is already registered')
        self._nodes[node.id] = node
        self._generate_mappings()

    def deregister(self, component):
        if component.id not in self._nodes:
            raise ValueError(f'Component {component.id} is not registered')
        del self._nodes[component.id]
        self._generate_mappings()

    def _generate_mappings(self):
        self._inputs_by_key = {}
        self._triggered_components_by_key = {}
        for node in self._nodes.values():
            for field in node.inputs.values():
                if field.key not in self._inputs_by_key:
                    self._inputs_by_key[field.key] = []
                self._inputs_by_key[field.key].append(field)
            for field in node.triggers:
                if field.key not in self._triggered_components_by_key:
                    self._triggered_components_by_key[field.key] = []
                self._triggered_components_by_key[field.key].append(node.component)

    def generate_links(self) -> List[Link]:
        links = []
        for source in self._nodes.values():
            for target in self._nodes.values():
                for source_field in source.outputs.values():
                    for target_field in target.inputs.values():
                        if source_field.key == target_field.key:
                            link = Link(source_field.key, source.id, source_field, target.id, target_field)
                            links.append(link)
        return links

    def inputs_by_key(self, key: str) -> [InputField]:
        return self._inputs_by_key.get(key, [])

    def triggered_component_by_key(self, key: str) -> [Component]:
        return self._triggered_components_by_key.get(key, [])

    def components(self) -> [Component]:
        return (node.component for node in self._nodes.values())

    def nodes(self) -> [ComponentNode]:
        return self._nodes.values()


def draw_application_graph(graph: ApplicationGraph):
    dot = graphviz.Digraph(node_attr={'shape': 'plaintext'}, graph_attr={'rankdir': 'LR'})
    for node in graph.nodes():
        dot.node(node.id, _create_node_html(node))
    for link in graph.generate_links():
        color = '#808080' if link.key.startswith('async2v') else 'black'
        dot.edge(f'{link.source}:{link.source_field.key}:e',
                 f'{link.target}:{link.target_field.key}:w',
                 label=link.key, color=color, fontcolor=color)
    dot.render(filename='graph.svg')


def _create_node_html(node: ComponentNode) -> str:
    left_rows = []
    for key, field in node.inputs.items():
        left_rows.append(_create_port_html(key, field, 'left'))
    left_column = _create_port_column(left_rows)
    right_rows = []
    for key, field in node.outputs.items():
        if key == '_Component__shutdown':
            continue
        right_rows.append(_create_port_html(key, field, 'right'))
    right_column = _create_port_column(right_rows)

    if isinstance(node.component, IteratingComponent):
        fps = node.component.target_fps
        clock = f' <font color="#808080">⌚ {fps} fps</font>'
    else:
        clock = ''

    return f'''<<table cellborder="0" style="rounded" color="#808080">
            <tr>
                <td colspan="3"><font point-size="18">{node.id}</font>{clock}</td>
            </tr>
            <tr>
                <td width="120">{left_column}</td>
                <td width="40"></td>
                <td width="120">{right_column}</td>
            </tr> 
        </table>>'''


def _create_port_html(key, field, align):
    color = _color_by_field(field)
    font = _font_by_field(field)
    return f'<tr><td width="120" height="24" fixedsize="TRUE" align="{align}" bgcolor="{color}" port="{field.key}"><font face="{font}">{key}</font></td></tr>'


def _color_by_field(field):
    if isinstance(field, DoubleBufferedField):
        if field.trigger:
            return '#A0F0A0'
        else:
            return '#80B0F0'
    else:
        return '#E0E0E0'


def _font_by_field(field):
    return 'courier italic' if field.key.startswith('async2v') else 'courier'


def _create_port_column(rows: List[str]) -> str:
    if len(rows) == 0:
        return ''
    else:
        return f'<table border="0" cellborder="1" cellspacing="3" width="100">\n' + '\n'.join(rows) + '\n</table>'
