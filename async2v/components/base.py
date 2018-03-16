from typing import List, Tuple

import logwood

from async2v.event import SHUTDOWN_EVENT
from async2v.fields import Output


class _BaseComponent:
    __count = {}

    def __new__(cls, *args, **kwargs):
        if cls.__name__ not in cls.__count:
            cls.__count[cls.__name__] = 0
        __instance = super().__new__(cls)
        __instance._numeric_id = cls.__count[cls.__name__]
        __instance.logger = logwood.get_logger(__instance.id)
        __instance.__shutdown = Output(SHUTDOWN_EVENT)
        cls.__count[cls.__name__] += 1
        return __instance

    def shutdown(self):
        self.__shutdown.push(None)

    @property
    def id(self) -> str:
        return self.__class__.__name__ + str(self._numeric_id)

    @property
    def graph_colors(self) -> Tuple[str, str]:
        return '#808080', '#FEFEFE'


class Component(_BaseComponent):

    async def setup(self):
        pass

    async def cleanup(self):
        pass


class IteratingComponent(Component):

    @property
    def target_fps(self) -> int:
        raise NotImplementedError

    async def process(self):
        raise NotImplementedError


class EventDrivenComponent(Component):

    async def process(self):
        raise NotImplementedError


class BareComponent(Component):
    pass


class SubComponent(_BaseComponent):
    pass


class ContainerMixin:

    def __init__(self, sub_components: List[SubComponent]):
        self._sub_components = sub_components

    @property
    def sub_components(self) -> List[SubComponent]:
        return self._sub_components
