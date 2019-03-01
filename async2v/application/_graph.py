from dataclasses import dataclass
from typing import List

import graphviz

from async2v.components.base import IteratingComponent
from async2v.fields import DoubleBufferedField
from . import Registry
from ._registry import ComponentNode, FieldNode


def get_formats() -> List[str]:
    return list(graphviz.FORMATS)


@dataclass
class Link:
    key: str
    source_component: str
    source_field_id: str
    target_component: str
    target_field_id: str


class ApplicationGraph:

    def __init__(self, registry: Registry):
        self._registry = registry
        self._dot = None  # type: graphviz.Digraph

    def draw(self, filename, output_format='pdf'):
        self._build()
        self._dot.format = output_format
        self._dot.filename = filename
        # noinspection PyArgumentList
        self._dot.render()

    def source(self):
        self._build()
        return self._dot.source

    def _build(self):
        if self._dot is not None:
            return
        self._dot = graphviz.Digraph(node_attr={'shape': 'plaintext'}, graph_attr={'rankdir': 'LR'})
        for node in self._registry.nodes():
            self._dot.node(node.id, '<' + self._create_node_html(node) + '>')
        for link in self._generate_links():
            color = '#808080' if link.key.startswith('async2v') else 'black'
            self._dot.edge(f'{link.source_component}:{link.source_field_id}:e',
                           f'{link.target_component}:{link.target_field_id}:w',
                           label=link.key, color=color, fontcolor=color)

    def _generate_links(self) -> List[Link]:
        links = []
        for source in self._registry.nodes():
            for target in self._registry.nodes():
                for source_field_node in source.all_outputs:
                    for target_field_node in target.all_inputs:
                        if source_field_node.key == target_field_node.key:
                            link = Link(source_field_node.key, source.id, source_field_node.field_id,
                                        target.id, target_field_node.field_id)
                            links.append(link)
        return links

    @classmethod
    def _create_node_html(cls, node: ComponentNode, sub: bool = False) -> str:
        left_rows = []
        for field_node in sorted(node.inputs, key=lambda it: it.field_name):
            left_rows.append(cls._create_port_html(field_node, 'left'))
        left_column = cls._create_port_column(left_rows)
        right_rows = []
        for field_node in sorted(node.outputs, key=lambda it: it.field_name):
            if field_node.field_name == '_BaseComponent__shutdown':
                continue
            right_rows.append(cls._create_port_html(field_node, 'right'))
        right_column = cls._create_port_column(right_rows)

        if isinstance(node.component, IteratingComponent):
            fps = node.component.target_fps
            clock = f' <font color="#808080">⌚ {fps} fps</font>'
        else:
            clock = ''

        sub_component_html = ''
        for sub_component in node.sub_components:
            sub_component_html += '<tr><td colspan="3">' + cls._create_node_html(sub_component, sub=True) + '</td></tr>'

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

    @classmethod
    def _create_port_html(cls, field_node: FieldNode, align):
        color = cls._color_by_field(field_node.field)
        font = cls._font_by_field(field_node.field)
        return f'<tr><td width="120" height="24" fixedsize="TRUE" align="{align}" bgcolor="{color}" ' \
               f'port="{field_node.field_id}"><font face="{font}">{field_node.field_name}</font></td></tr>'

    @staticmethod
    def _color_by_field(field):
        if isinstance(field, DoubleBufferedField):
            if field.trigger:
                return '#A0F0A0'
            else:
                return '#80B0F0'
        else:
            return '#E0E0E0'

    @staticmethod
    def _font_by_field(field):
        return 'courier italic' if field.key.startswith('async2v') else 'courier'

    @staticmethod
    def _create_port_column(rows: List[str]) -> str:
        if len(rows) == 0:
            return ''
        else:
            return f'<table border="0" cellborder="1" cellspacing="3" width="100">\n' + '\n'.join(rows) + '\n</table>'
