from typing import TypeVar, Generic

import time

REGISTER_EVENT = 'async2v.register'
DEREGISTER_EVENT = 'async2v.deregister'
SHUTDOWN_EVENT = 'async2v.shutdown'
OPENCV_FRAME_EVENT = 'async2v.opencv.frame'
DURATION_EVENT = 'async2v.duration'
FPS_EVENT = 'async2v.fps'

T = TypeVar('T')


class Event(Generic[T]):
    """
    Envelope for all data passed between components.

    The key serves as an address: Events are delivered to all input `fields` that listen to the key specified in the
    event. There is no need to explicitly construct events in production code, as the `Output` field takes care of that.

    `Event` is a generic type, use :code:`Event[T]` to denote an event of type :code:`T`.
    """

    __slots__ = ['timestamp', 'key', 'timestamp', 'value']

    def __init__(self, key: str, value: T = None, timestamp: float = None):
        if timestamp is None:
            timestamp = time.time()

        #: Address that connects output to input `fields`
        self.key = key  # type: str
        #: Timestamp of the event in seconds since the epoch
        self.timestamp = timestamp  # type: float
        #: Payload
        self.value = value  # type: T

    def __str__(self):
        return f'Event({self.key}, {self.value})'
