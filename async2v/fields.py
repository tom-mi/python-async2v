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
    def __init__(self, key: str, trigger: bool = False):
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
    def __init__(self, key: str, trigger: bool = False):
        super().__init__(key, trigger=trigger)
        self._input_event = None  # type: Event[T]
        self._event = None  # type: Event[T]

    def _set_event(self, new: Event[T]) -> None:
        self._input_event = new

    def _switch_events(self) -> None:
        self._event = self._input_event

    @property
    def event(self) -> Event[T]:
        return self._event

    @property
    def value(self) -> Optional[T]:
        if self._event is None:
            return None
        return self._event.value

    @property
    def timestamp(self) -> float:
        return self._event.timestamp


class LatestBy(Generic[K, T], DoubleBufferedField[T]):

    def __init__(self, key: str, classifier: Callable[[T], K], trigger: bool = False):
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
        return self._events

    @property
    def value_dict(self) -> Dict[K, T]:
        return dict((k, v.value) for k, v in self._events.items())

    @property
    def timestamps(self) -> Dict[K, float]:
        return dict((k, v.timestamp) for k, v in self._events.items())


class Buffer(DoubleBufferedField[T], Generic[T]):

    def __init__(self, key: str, maxlen: int = None, trigger: bool = False):
        super().__init__(key, trigger=trigger)
        self._input_buffer = deque(maxlen=maxlen)
        self._events = []  # type: List[Event[T]]
        self._values = []  # type: List[T]
        self._timestamps = []  # type: List[float]

    @property
    def events(self) -> List[Event[T]]:
        return self._events

    @property
    def values(self) -> List[T]:
        return self._values

    @property
    def timestamps(self) -> List[float]:
        return self._timestamps

    def _set_event(self, new: T) -> None:
        self._input_buffer.append(new)

    def _switch_events(self):
        self._events = list(self._input_buffer)
        self._values = [e.value for e in self._events]
        self._timestamps = [e.timestamp for e in self._events]
        self._input_buffer.clear()


class History(DoubleBufferedField[T], Generic[T]):

    def __init__(self, key: str, maxlen: int, trigger: bool = False):
        super().__init__(key, trigger=trigger)
        self._input_buffer = deque(maxlen=maxlen)
        self._events = []  # type: [Event[T]]
        self._values = []  # type: [T]
        self._timestamps = []  # type: [float]

    @property
    def events(self) -> [Event[T]]:
        return self._events

    @property
    def values(self) -> [T]:
        return self._values

    @property
    def timestamps(self) -> [float]:
        return self._timestamps

    def _set_event(self, new: Event[T]) -> None:
        self._input_buffer.append(new)

    def _switch_events(self) -> None:
        self._events = list(self._input_buffer)
        self._values = [e.value for e in self._events]
        self._timestamps = [e.timestamp for e in self._events]


class InputQueue(InputField[T], Generic[T]):

    def __init__(self, key: str, maxlen: int = None):
        super().__init__(key)
        self._queue = deque(maxlen=maxlen)

    def set(self, new: Event[T]) -> None:
        self._queue.append(new)

    @property
    def queue(self) -> deque:
        """
        Get the input deque, which contains incoming events of type event.Event.
        New events are appended at the end of the queue by the framework.
        """
        return self._queue


class Output(Generic[T]):
    def __init__(self, key: str):
        self._key = key  # type: str
        self._queue = None  # type: queue.Queue

    def set_queue(self, queue_: Optional[queue.Queue]):
        """
        This method is used by the framework to inject the central application queue.
        You should not need to call this method from your production code.
        """
        self._queue = queue_

    @property
    def key(self) -> str:
        return self._key

    def push(self, value: T, timestamp: float = None):
        self._queue.put(Event(self._key, value, timestamp))


class AveragingOutput(Output[T], Generic[T]):
    """
    Push the average of the values collected every count values or after the given interval, whichever happens first.
    The value type T needs to support __add__(T, T) and __truediv__(T, int) to compute a meaningful average.
    """

    def __init__(self, key: str, count: int = None, interval: float = None):
        super().__init__(key)
        if count is None and interval is None:
            raise ConfigurationError('Please specify at least one of count or interval')
        self._buffer = []
        self._last_pushed = 0
        self._count = count
        self._interval = interval

    def push(self, value: T, timestamp: float = None):
        self._buffer.append(value)
        if ((self._count and len(self._buffer) >= self._count) or
                (self._interval and time.time() - self._last_pushed > self._interval)):
            value = sum(self._buffer[1:], self._buffer[0]) / len(self._buffer)
            super().push(value, timestamp)
            self._last_pushed = time.time()
            self._buffer = []
