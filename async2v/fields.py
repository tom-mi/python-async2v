import asyncio
import queue
from collections import deque
from typing import TypeVar, Generic, Optional, Dict, Callable, List

import time

from async2v.error import ConfigurationError
from async2v.event import Event

T = TypeVar('T')
K = TypeVar('K')


class InputField(Generic[T]):
    """
    Abstract base class for all input fields
    """

    def __init__(self, key: str):
        self._key = key  # type: str

    @property
    def key(self) -> str:
        return self._key

    def set(self, new: Event[T]) -> None:
        """
        Push new event into the field.

        This method is used by the framework to push events to components.
        You should not need to call this method from your production code.
        """
        raise NotImplementedError


class DoubleBufferedField(InputField[T], Generic[T]):
    """
    Abstract base class for most input fields

    Implements double buffering to guarantee components stable content of their input fields during one processing step,
    even if new events are arriving meanwhile.
    """

    def __init__(self, key: str, trigger: bool = False):
        """
        :param key: Address that connects output to input fields
        :param trigger: Set to `True` to trigger processing step when a new `Event` arrives. Only allowed within a
                         `EventDrivenComponent`.
        """
        super().__init__(key)
        self._key = key  # type: str
        self._trigger = trigger  # type: bool
        self._input_updated = asyncio.Event()  # type: asyncio.Event
        self._updated = False  # type: bool

    @property
    def trigger(self) -> bool:
        return self._trigger

    @property
    def updated(self) -> bool:
        return self._updated

    def set(self, new: Event[T]) -> None:
        self._input_updated.set()
        self._set_event(new)

    def _set_event(self, new: Event[T]) -> None:
        raise NotImplementedError

    def switch(self) -> None:
        """
        Switch the double buffer.

        This method is used by the framework to make new values available for the next processing step.
        You should not need to call this method from your production code.
        """
        self._updated = self._input_updated.is_set()
        self._switch_events()
        self._input_updated.clear()

    def _switch_events(self) -> None:
        raise NotImplementedError


class Latest(DoubleBufferedField[T], Generic[T]):
    """
    Provides the latest received event to the component
    """

    def __init__(self, key: str, trigger: bool = False):
        """
        :param key: Address that connects output to input fields
        :param trigger: Set to `True` to trigger processing step when a new `Event` arrives. Only allowed within a
                         `EventDrivenComponent`.
        """
        super().__init__(key, trigger=trigger)
        self._input_event = None  # type: Event[T]
        self._event = None  # type: Event[T]

    def _set_event(self, new: Event[T]) -> None:
        self._input_event = new

    def _switch_events(self) -> None:
        self._event = self._input_event

    @property
    def event(self) -> Event[T]:
        """
        Latest received event

        `None` if no event has been received.
        """
        return self._event

    @property
    def value(self) -> Optional[T]:
        """
        Value of latest received event

        `None` if no event has been received.
        """
        if self._event is None:
            return None
        return self._event.value

    @property
    def timestamp(self) -> float:
        """
        Timestamp of the latest received event.
        """
        return self._event.timestamp


class LatestBy(Generic[K, T], DoubleBufferedField[T]):
    """
    Provides the latest received event to the component by category

    Incoming events are assigned to categories by the given ``classifier`` function. For each event class,
    the latest event is retained (the same way as in the `Latest` field).
    The latest events per category can be accessed as `dict`.

    Example storing the latest message of a specific length:
        >>> message_by_length = LatestBy[str, int]('message', lambda m: len(m))
        >>> # The following 4 lines simulate the framework delivering events
        >>> message_by_length.set(Event[str]('message', 'Hello'))
        >>> message_by_length.set(Event[str]('message', 'World'))
        >>> message_by_length.set(Event[str]('message', 'Hello World!'))
        >>> message_by_length.switch()
        >>> # The latest values are available by category
        >>> message_by_length.value_dict
        {5: 'World', 12: 'Hello World!'}
    """

    def __init__(self, key: str, classifier: Callable[[T], K], trigger: bool = False):
        """
        :param key: Address that connects output to input fields
        :param classifier: Function to sort input events of type ``Event[T]`` into categories of type ``K``.
        :param trigger: Set to `True` to trigger processing step when a new `Event` arrives. Only allowed within a
                         `EventDrivenComponent`.
        """
        super().__init__(key, trigger=trigger)
        self._classifier = classifier
        self._input_events = {}  # type: Dict[K, Event[T]]
        self._events = {}  # type: Dict[K, Event[T]]

    def _set_event(self, new: Event[T]) -> None:
        event_class = self._classifier(new.value)
        self._input_events[event_class] = new

    def _switch_events(self) -> None:
        self._events = self._input_events.copy()

    @property
    def events(self) -> Dict[K, Event[T]]:
        """
        Latest received events per category

        Empty `dict` if no event has been received.
        """
        return self._events

    @property
    def value_dict(self) -> Dict[K, T]:
        """
        Values of latest received events per category

        Empty `dict` if no event has been received.
        """
        return dict((k, v.value) for k, v in self._events.items())

    @property
    def timestamps(self) -> Dict[K, float]:
        """
        Timestamps of latest received events per category

        Empty `dict` if no event has been received.
        """
        return dict((k, v.timestamp) for k, v in self._events.items())


class Buffer(DoubleBufferedField[T], Generic[T]):
    """
    Provides all events received since the last processing step

    In the next processing step, the buffer contains only events received after the ones from the previous step.
    """

    def __init__(self, key: str, maxlen: int = None, trigger: bool = False):
        """
        :param key: Address that connects output to input fields
        :param trigger: Set to `True` to trigger processing step when a new `Event` arrives. Only allowed within a
                         `EventDrivenComponent`.
        """
        super().__init__(key, trigger=trigger)
        self._input_buffer = deque(maxlen=maxlen)
        self._events = []  # type: List[Event[T]]
        self._values = []  # type: List[T]
        self._timestamps = []  # type: List[float]

    @property
    def events(self) -> List[Event[T]]:
        """
        All events received since the last processing step in received order.

        Empty list if no event has been received.
        """
        return self._events

    @property
    def values(self) -> List[T]:
        """
        Values of all events received since the last processing step in received order.

        Empty list if no event has been received.
        """
        return self._values

    @property
    def timestamps(self) -> List[float]:
        """
        Timestamps of all events received since the last processing step in received order.

        Empty list if no event has been received.
        """
        return self._timestamps

    def _set_event(self, new: T) -> None:
        self._input_buffer.append(new)

    def _switch_events(self):
        self._events = list(self._input_buffer)
        self._values = [e.value for e in self._events]
        self._timestamps = [e.timestamp for e in self._events]
        self._input_buffer.clear()


class History(DoubleBufferedField[T], Generic[T]):
    """
    Provides the last ``maxlen`` events

    Other than the `Buffer` field, a `History` field may provide events that have already been processed again, as
    the events are not cleared between processing steps. It works like a `Latest` field that can store more than one
    historic value.
    """

    def __init__(self, key: str, maxlen: int, trigger: bool = False):
        """
        :param key: Address that connects output to input fields
        :param maxlen: Maximum number of events to retain
        :param trigger: Set to `True` to trigger processing step when a new `Event` arrives. Only allowed within a
                         `EventDrivenComponent`.
        """
        super().__init__(key, trigger=trigger)
        self._input_buffer = deque(maxlen=maxlen)
        self._events = []  # type: List[Event[T]]
        self._values = []  # type: [T]
        self._timestamps = []  # type: [float]

    @property
    def events(self) -> List[Event[T]]:
        """
        The last ``maxlen`` events in received order.

        Empty list if no event has been received.
        """
        return self._events

    @property
    def values(self) -> List[T]:
        """
        The values of the last ``maxlen`` events in received order.

        Empty list if no event has been received.
        """
        return self._values

    @property
    def timestamps(self) -> List[float]:
        """
        The timestamps of the last ``maxlen`` events in received order.

        Empty list if no event has been received.
        """
        return self._timestamps

    def _set_event(self, new: Event[T]) -> None:
        self._input_buffer.append(new)

    def _switch_events(self) -> None:
        self._events = list(self._input_buffer)
        self._values = [e.value for e in self._events]
        self._timestamps = [e.timestamp for e in self._events]


class InputQueue(InputField[T], Generic[T]):
    """
    Unmanaged input field appending incoming events to a queue

    This input field is useful for components that don't rely on the framework to trigger processing steps (subclasses
    of `BareComponent`). Internally, a `deque <collections.deque>` is used, which is safe for threading scenarios (as
    long asjyou use `popleft() <collections.deque.popleft>` to read events).
    """

    def __init__(self, key: str, maxlen: int = None):
        super().__init__(key)
        self._queue = deque(maxlen=maxlen)

    def set(self, new: Event[T]) -> None:
        self._queue.append(new)

    @property
    def queue(self) -> deque:
        """
        Get the input deque, which contains incoming events of type `Event`.
        New events are appended at the end of the queue by the framework.
        """
        return self._queue


class Output(Generic[T]):
    """
    All-purpose output field

    Push events here during processing. They will be routed to all relevant input fields (matched by key).
    """

    def __init__(self, key: str):
        """
        :param key: Address that connects output to input fields
        """
        self._key: str = key
        self._queue: queue.Queue = None

    def set_queue(self, queue_: Optional[queue.Queue]):
        """
        This method is used by the framework to inject the central application queue.
        You should not need to call this method from your production code.
        """
        self._queue = queue_

    @property
    def key(self) -> str:
        return self._key

    def push(self, value: T, timestamp: float = None) -> None:
        """
        Push a new output value

        :param value: Payload
        :param timestamp: Will be set to current time if not given. Set this field if you want to propagate the
            timestamp of a source event.
        """
        self._queue.put(Event(self._key, value, timestamp))


class AveragingOutput(Output[T], Generic[T]):
    """
    Averaging output field

    Push the average of the values collected every count values or after the given interval, whichever happens first.
    The value type ``T`` needs to support ``__add__(T, T)`` and ``__truediv__(T, int)`` to compute a meaningful average.

    An event can only be emitted during a call to `push`. If the interval is expired but no further values
    are pushed, no output is generated.

    This field is intended for special use cases like metrics. For example, it is used by the framework to
    report performance indicators (fps, processing time).
    """

    def __init__(self, key: str, count: int = None, interval: float = None):
        """
        :param key: Address that connects output to input fields
        :param count: Maximum number of values to average over
        :param interval: Maximum time in seconds to collect values to average over
        """
        super().__init__(key)
        if count is None and interval is None:
            raise ConfigurationError('Please specify at least one of count or interval')
        self._buffer = []
        self._last_pushed = 0
        self._count = count
        self._interval = interval

    def push(self, value: T, timestamp: float = None):
        """
        Push a new output value

        Depending on the configuration if this field, not all pushed values cause new events to be emitted.

        :param value: Payload
        :param timestamp: Will be set to current time if not given. Set this field if you want to propagate the
            timestamp of a source event.
        """
        self._buffer.append(value)
        if ((self._count and len(self._buffer) >= self._count) or
                (self._interval and time.time() - self._last_pushed > self._interval)):
            value = sum(self._buffer[1:], self._buffer[0]) / len(self._buffer)
            super().push(value, timestamp)
            self._last_pushed = time.time()
            self._buffer = []
