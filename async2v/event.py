from typing import TypeVar, Generic

import time

REGISTER_EVENT = 'async2v.register'
"""
:type: str

Internal event key. Components to be registered are published as payload on this key.

Don't use directly - To register a component, use the `register` method on the `Application`.
"""

DEREGISTER_EVENT = 'async2v.deregister'
"""
:type: str

Internal event key. Components to be de-registered are published as payload on this key.

Don't use directly - To de-register a component, use the `deregister` method on the `Application`.
"""

SHUTDOWN_EVENT = 'async2v.shutdown'
"""
:type: str

Internal event key used to trigger application shutdown.

Don't use directly - To shutdown, call `shutdown` from within a component.
"""

SHUTDOWN_DUE_TO_ERROR = 'async2v.shutdown_due_to_error'
"""
:type: str

Internal event key used to trigger application shutdown due to an uncaught exception in one of the components.

Don't use directly. From a `EventDrivenComponent` or `IteratingComponent`, shutdown can be triggered by raising an
exception within the processing logic.
"""

OPENCV_FRAME_EVENT = 'async2v.opencv.frame'
"""
:type: str

Event key to collect debug frames. Push events containing `Frame` payload to this key to have them displayed in the
`OpenCvDebugDisplay`.
"""

DURATION_EVENT = 'async2v.duration'
"""
:type: str

Metric events containing `Duration` payload are pushed on this event key by the framework.
"""

FPS_EVENT = 'async2v.fps'
"""
:type: str

Metric events containing `Fps` payload are pushed on this event key by the framework.
"""

T = TypeVar('T')


class Event(Generic[T]):
    """
    Envelope for all data passed between components.

    The key serves as an address: Events are delivered to all input `fields` that listen to the key specified in the
    event. There is no need to explicitly construct events in production code, as the `Output` field takes care of that.

    `Event` is a generic type, use :code:`Event[T]` to denote an event with a value of type :code:`T`.
    """

    __slots__ = ['timestamp', 'key', 'timestamp', 'value']

    def __init__(self, key: str, value: T = None, timestamp: float = None):
        """

        :param key: Address that connects output to input `fields`
        :param value: Payload
        :param timestamp: Set to current time if not provided
        """
        if timestamp is None:
            timestamp = time.time()

        self.key: str = key
        """
        :type: str

        Address that connects output to input `fields`
        """

        self.timestamp: float = timestamp
        """
        :type: float

        Timestamp of the event in seconds since the epoch
        """

        self.value: T = value
        """
        :type: T

        Payload
        """

    def __str__(self):
        return f'Event({self.key}, {self.value})'
