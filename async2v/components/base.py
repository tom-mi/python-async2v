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
        """
        Trigger graceful shutdown of the application.
        """
        self.__shutdown.push(None)

    @property
    def id(self) -> str:
        """
        Human readable component id, created from class name and ascending index (e.g. ``VideoSource0``).
        """
        return self.__class__.__name__ + str(self._numeric_id)

    @property
    def graph_colors(self) -> Tuple[str, str]:
        """
        Override to provide custom colors for the application graph that can be generated with the ``graph`` command.

        :return: (background color, foreground color) as hex RGB string (e.g. ``#808080``)
        """
        return '#808080', '#FEFEFE'


class Component(_BaseComponent):
    """
    Abstract base class for all components

    For building components, use one of the available subclasses:

    * `IteratingComponent`
    * `EventDrivenComponent`
    * `BareComponent`

    .. autoattribute:: id
    .. autoattribute:: graph_colors
    .. automethod:: shutdown
    """

    async def setup(self) -> None:
        """
        Can be overridden to perform setup before processing starts.

        This method is run after registration and app startup, i.e. all inputs & outputs are wired and can be used.
        """

    async def cleanup(self) -> None:
        """
        Can be overridden to perform cleanup before the component is shut down.

        This method is run before unregistering the component. The inputs & outputs are still wired and can be used,
        but other components might not be reacting to those events any more as they have already been shut down.
        """


class IteratingComponent(Component):
    """
    Runs at a fixed frame rate

    The iterating component is triggered by the framework regularly. It tries to run the `process` method in a way
    that the target frame rate is achieved. However, as other factors like runtime of other components are
    involved and the available processing time is limited, you should not rely on an exact frame rate.

    .. autocomethod:: setup
    .. autocomethod:: cleanup
    """

    @property
    def target_fps(self) -> int:
        """
        Must be overridden to specify the target processing rate in Hz.

        This method is only called once during startup of the component. It is not possible to change the
        target frame rate during runtime.
        """
        raise NotImplementedError

    async def process(self) -> None:
        """
        Must be overridden to implement the component's core logic.

        This method is called by the framework regularly at approximately the rate returned by `target_fps`.

        It is never called before :py:meth:`setup` or after :py:meth:`cleanup` has been called for this component.
        """
        raise NotImplementedError


class EventDrivenComponent(Component):
    """
    Runs when trigger events are received

    An `EventDrivenComponent` needs to have at least one trigger field (a `DoubleBufferedField` like `Latest` or
    `Buffer` constructed with ``trigger=True``). When one of the trigger fields receives an event, the component is
    marked for execution. Its `process` method will be invoked when the component runner is given control by the asyncio
    scheduler. That does not happen immediately - further events (also on different fields) can arrive between the
    trigger and the actual invocation of the `process` method. Those events don't lead to additional invocations.

    The guarantees by the framework are:

    * if this method has been called, at least one event has arrived on any of the trigger fields
    * if any of the trigger fields receives an event, a method invocation is scheduled and performed as soon as
      possible (if not already scheduled)

    .. autocomethod:: setup
    .. autocomethod:: cleanup
    """

    async def process(self) -> None:
        """
        Must be overridden to implement the component's core logic.

        It is never called before :py:meth:`setup` or after :py:meth:`cleanup` has been called for this component.
        """
        raise NotImplementedError


class BareComponent(Component):
    """
    Unmanaged component

    This component's processing steps are not managed by the framework. Therefore, it cannot have any
    `DoubleBufferedField` fields, as those require the framework to know when the processing happens.
    The only builtin input field supported in this component is `InputQueue`.

    Use this component for special cases like reading from external event sources or running all of the components logic
    in a separate thread.

    .. autocomethod:: setup
    .. autocomethod:: cleanup
    """


class SubComponent(_BaseComponent):
    """
    Dependent component

    A `SubComponent` is unmanaged with respect to processing, but it needs to be embedded into another component.
    It can have its own input & output fields. Processing needs to be triggered by the containing component.
    The containing component needs to extend from the `ContainerMixin` and register its supcomonents.

    It is intended to support the composite pattern to design complex components.

    Example usage:

        >>> class SampleSubComponent(SubComponent):
        >>>
        >>>     def __init__(self):
        >>>         self.input = Buffer('in', trigger=True)
        >>>         self.output = Output('out')
        >>>
        >>>     def do_something(self):
        >>>         for value in self.input.values:
        >>>             self.output.push(value)
        >>>
        >>>
        >>> class SampleComponent(EventDrivenComponent, ContainerMixin):
        >>>
        >>>     def __init__(self, sample: SampleSubComponent):
        >>>         super().__init__([sample])
        >>>
        >>>     async def process(self):
        >>>         for sub_component in self.sub_components:
        >>>             sub_component.do_something()
    """


class ContainerMixin:
    """
    Mixin allowing components to have subcomponents.

    See `SubComponent` for more information.
    """

    def __init__(self, sub_components: List[SubComponent]):
        self._sub_components = sub_components

    @property
    def sub_components(self) -> List[SubComponent]:
        """
        :return: All registered subcomponents of this component
        """
        return self._sub_components
