from typing import TypeVar, Generic

import time

REGISTER_EVENT = 'async2v.register'
DEREGISTER_EVENT = 'async2v.deregister'
SHUTDOWN_EVENT = 'async2v.shutdown'

T = TypeVar('T')


class Event(Generic[T]):
    def __init__(self, key: str, value: T = None, timestamp: float = None):
        if timestamp is None:
            timestamp = time.time()
        self.key = key
        self.timestamp = timestamp
        self.value = value

    def __str__(self):
        return f'Event({self.key}, {self.value})'
