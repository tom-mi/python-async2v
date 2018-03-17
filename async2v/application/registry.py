from typing import Dict, List, Union, NamedTuple

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


class Registry:

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
