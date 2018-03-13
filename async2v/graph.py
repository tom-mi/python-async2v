import typing
from typing import Dict, List

from async2v.components.base import Component
from async2v.fields import InputField, Output, DoubleBufferedField


class ComponentNode(typing.NamedTuple):
    component: Component
    inputs: List[InputField]
    outputs: List[Output]
    triggers: List[InputField]

    @property
    def id(self) -> str:
        return self.component.id

    @staticmethod
    def create(component: Component) -> 'ComponentNode':
        inputs = [f for f in vars(component).values() if isinstance(f, InputField)]
        outputs = [f for f in vars(component).values() if isinstance(f, Output)]
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
        self._links = []
        self._inputs_by_key = {}
        self._triggered_components_by_key = {}
        for node in self._nodes.values():
            for field in node.inputs:
                if field.key not in self._inputs_by_key:
                    self._inputs_by_key[field.key] = []
                self._inputs_by_key[field.key].append(field)
            for field in node.triggers:
                if field.key not in self._triggered_components_by_key:
                    self._triggered_components_by_key[field.key] = []
                self._triggered_components_by_key[field.key].append(node.component)

    def _generate_links(self):
        links = []
        for source in self._nodes.values():
            for target in self._nodes.values():
                for source_field in source.outputs:
                    for target_field in target.inputs:
                        if source_field.key == target_field.key:
                            link = Link(source_field.key, source.id, source_field, target.id, target_field)
                            self._links.append(link)
        return links

    def inputs_by_key(self, key: str) -> [InputField]:
        return self._inputs_by_key.get(key, [])

    def triggered_component_by_key(self, key: str) -> [Component]:
        return self._triggered_components_by_key.get(key, [])

    def components(self) -> [Component]:
        return (node.component for node in self._nodes.values())
