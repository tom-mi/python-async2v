from typing import Dict, List, Union, NamedTuple

import graphviz

from async2v.components.base import Component, IteratingComponent, SubComponent, ContainerMixin, EventDrivenComponent, \
    BareComponent
from async2v.error import ConfigurationError
from async2v.fields import InputField, Output, DoubleBufferedField


class ComponentNode(NamedTuple):
    component: Union[Component, SubComponent]
    inputs: Dict[str, InputField]
    outputs: Dict[str, Output]
    triggers: List[InputField]
    sub_components: List['ComponentNode']

    @property
    def id(self) -> str:
        return self.component.id

    @staticmethod
    def create(component: Union[Component, SubComponent]) -> 'ComponentNode':
        inputs = dict((k, f) for k, f in vars(component).items() if isinstance(f, InputField))
        outputs = dict((k, f) for k, f in vars(component).items() if isinstance(f, Output))
        triggers = [f for f in vars(component).values() if isinstance(f, DoubleBufferedField) and f.trigger]
        sub_components = []
        if isinstance(component, ContainerMixin):
            for sub_component in component.sub_components:
                sub_components.append(ComponentNode.create(sub_component))

        return ComponentNode(component, inputs, outputs, triggers, sub_components)

    @property
    def all_inputs(self) -> Dict[str, InputField]:
        result = {}
        result.update(self.inputs)
        for sub_component in self.sub_components:
            for k, field in sub_component.all_inputs.items():
                result[self.id + '.' + k] = field
        return result

    @property
    def all_outputs(self) -> Dict[str, Output]:
        result = {}
        result.update(self.outputs)
        for sub_component in self.sub_components:
            for k, field in sub_component.all_outputs.items():
                result[self.id + '.' + k] = field
        return result

    @property
    def all_triggers(self) -> List[InputField]:
        result = []
        result += self.triggers
        for sub_component in self.sub_components:
            result += sub_component.all_triggers
        return result


class Link(NamedTuple):
    key: str
    source_component: str
    source_field_name: str
    target_component: str
    target_field_name: str


class ApplicationGraph:

    def __init__(self):
        self._nodes = {}  # type: Dict[str, ComponentNode]
        # all following fields are re-generated on each state change
        self._inputs_by_key = {}  # type: Dict[str, List[InputField]]
        self._triggered_components_by_key = {}  # type: Dict[str, List[Component]]

    def register(self, component):
        node = ComponentNode.create(component)
        self._validate(node)
        if node.id in self._nodes:
            raise ValueError(f'Component {node.id} is already registered')
        self._nodes[node.id] = node
        self._generate_mappings()

    def deregister(self, component):
        if component.id not in self._nodes:
            raise ValueError(f'Component {component.id} is not registered')
        del self._nodes[component.id]
        self._generate_mappings()

    @staticmethod
    def _validate(node: ComponentNode):
        if isinstance(node.component, IteratingComponent):
            if len(node.all_triggers) > 0:
                raise ConfigurationError(f'IteratingComponent {node.id} cannot have trigger fields')
        elif isinstance(node.component, EventDrivenComponent):
            if len(node.all_triggers) == 0:
                raise ConfigurationError(f'EventDrivenComponent {node.id} must have at least one trigger field')
        elif isinstance(node.component, BareComponent):
            if len([f for f in node.all_inputs if isinstance(f, DoubleBufferedField)]) > 0:
                raise ConfigurationError(f'BareComponent {node.id} cannot have double-buffered fields')
        else:
            raise RuntimeError(f'Unknown component type {node.component.__class__.__name__} of {node.id}')

    def _generate_mappings(self):
        self._inputs_by_key = {}
        self._triggered_components_by_key = {}
        for node in self._nodes.values():
            self._add_fields(node)

    def _add_fields(self, node: ComponentNode):
        for field in node.all_inputs.values():
            if field.key not in self._inputs_by_key:
                self._inputs_by_key[field.key] = []
            self._inputs_by_key[field.key].append(field)
        for field in node.all_triggers:
            if field.key not in self._triggered_components_by_key:
                self._triggered_components_by_key[field.key] = []
            self._triggered_components_by_key[field.key].append(node.component)

    def generate_links(self) -> List[Link]:
        links = []
        for source in self._nodes.values():
            for target in self._nodes.values():
                for full_source_field_name, source_field in source.all_outputs.items():
                    for full_target_field_name, target_field in target.all_inputs.items():
                        if source_field.key == target_field.key:
                            source_field_name = full_source_field_name.split('.')[-1]
                            target_field_name = full_target_field_name.split('.')[-1]
                            link = Link(source_field.key, source.id, source_field_name, target.id, target_field_name)
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

    def node_by_component(self, component: Component) -> ComponentNode:
        return self._nodes[component.id]


def draw_application_graph(graph: ApplicationGraph, print_source: bool =False):
    dot = graphviz.Digraph(node_attr={'shape': 'plaintext'}, graph_attr={'rankdir': 'LR'})
    for node in graph.nodes():
        dot.node(node.id, '<' + _create_node_html(node) + '>')
    for link in graph.generate_links():
        color = '#808080' if link.key.startswith('async2v') else 'black'
        dot.edge(f'{link.source_component}:{link.source_field_name}:e',
                 f'{link.target_component}:{link.target_field_name}:w',
                 label=link.key, color=color, fontcolor=color)
    if print_source:
        print(dot.source)
    else:
        dot.render(filename='graph.svg')


def _create_node_html(node: ComponentNode, sub: bool = False) -> str:
    left_rows = []
    for field_name, field in sorted(node.inputs.items(), key=lambda it: it[0]):
        left_rows.append(_create_port_html(field_name, field, 'left'))
    left_column = _create_port_column(left_rows)
    right_rows = []
    for field_name, field in sorted(node.outputs.items(), key=lambda it: it[0]):
        if field_name == '_BaseComponent__shutdown':
            continue
        right_rows.append(_create_port_html(field_name, field, 'right'))
    right_column = _create_port_column(right_rows)

    if isinstance(node.component, IteratingComponent):
        fps = node.component.target_fps
        clock = f' <font color="#808080">⌚ {fps} fps</font>'
    else:
        clock = ''

    sub_component_html = ''
    for sub_component in node.sub_components:
        sub_component_html += '<tr><td colspan="3">' + _create_node_html(sub_component, sub=True) + '</td></tr>'

    font_size = 14 if sub else 18
    color, bg_color = node.component.graph_colors

    return f'''<table cellborder="0" style="rounded" color="{color}" bgcolor="{bg_color}">
            <tr>
                <td colspan="3"><font point-size="{font_size}">{node.id}</font>{clock}</td>
            </tr>
            <tr>
                <td width="120">{left_column}</td>
                <td width="40"></td>
                <td width="120">{right_column}</td>
            </tr> 
            {sub_component_html}
        </table>'''


def _create_port_html(field_name, field, align):
    color = _color_by_field(field)
    font = _font_by_field(field)
    return f'<tr><td width="120" height="24" fixedsize="TRUE" align="{align}" bgcolor="{color}" port="{field_name}"><font face="{font}">{field_name}</font></td></tr>'


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
