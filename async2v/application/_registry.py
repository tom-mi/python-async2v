from dataclasses import dataclass
from typing import Dict, List, Union, Generic, TypeVar

from async2v.components.base import Component, IteratingComponent, SubComponent, ContainerMixin, EventDrivenComponent, \
    BareComponent
from async2v.error import ConfigurationError
from async2v.fields import InputField, Output, DoubleBufferedField

F = TypeVar('F', InputField, Output)


class FieldNode(Generic[F]):
    __slots__ = ['field', 'field_id', 'field_name']

    def __init__(self, field: F, field_id: str, field_name: str):
        self.field = field  # type : F
        self.field_id = field_id  # type : str
        self.field_name = field_name  # type : str

    @property
    def key(self) -> str:
        return self.field.key


@dataclass
class ComponentNode:
    component: Union[Component, SubComponent]
    inputs: List[FieldNode[InputField]]
    outputs: List[FieldNode[Output]]
    triggers: List[FieldNode[InputField]]
    sub_components: List['ComponentNode']

    @property
    def id(self) -> str:
        return self.component.id

    @staticmethod
    def create(component: Union[Component, SubComponent], id_prefix: str = '') -> 'ComponentNode':
        id_prefix += component.id + '.'
        inputs = [FieldNode(f, id_prefix + k, k) for k, f in vars(component).items() if isinstance(f, InputField)]
        outputs = [FieldNode(f, id_prefix + k, k) for k, f in vars(component).items() if isinstance(f, Output)]
        triggers = [FieldNode(f, id_prefix + k, k) for k, f in vars(component).items() if
                    isinstance(f, DoubleBufferedField) and f.trigger]
        sub_components = []
        if isinstance(component, ContainerMixin):
            for sub_component in component.sub_components:
                sub_components.append(ComponentNode.create(sub_component, id_prefix=id_prefix))

        return ComponentNode(component, inputs, outputs, triggers, sub_components)

    @property
    def all_inputs(self) -> List[FieldNode[InputField]]:
        return self.inputs + [field for sub_component in self.sub_components for field in sub_component.all_inputs]

    @property
    def all_outputs(self) -> List[FieldNode[Output]]:
        return self.outputs + [field for sub_component in self.sub_components for field in sub_component.all_outputs]

    @property
    def all_triggers(self) -> List[FieldNode[InputField]]:
        return self.triggers + [field for sub_component in self.sub_components for field in sub_component.all_triggers]


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
        for field_node in node.all_inputs:
            if field_node.key not in self._inputs_by_key:
                self._inputs_by_key[field_node.key] = []
            self._inputs_by_key[field_node.key].append(field_node.field)
        for field_node in node.all_triggers:
            if field_node.key not in self._triggered_components_by_key:
                self._triggered_components_by_key[field_node.key] = []
            self._triggered_components_by_key[field_node.key].append(node.component)

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
