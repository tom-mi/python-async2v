from dataclasses import dataclass


@dataclass
class Fps:
    """
    Frames per second event payload

    Metric emitted on the `FPS_EVENT` for all components of type `IteratingComponent`
    """

    component_id: str
    """
    :type: str

    `component id <Component.id>` of emitting component
    """

    current: float
    """
    :type: float

    Current number of frames per second
    """

    target: int
    """"
    :type: int

    Target frames per second configured in component
    """

    def __add__(self, other: 'Fps'):
        if self.component_id != other.component_id:
            raise ValueError('Cannot add fps of different components')
        return Fps(self.component_id, self.current + other.current, self.target)

    def __truediv__(self, other: int):
        return Fps(self.component_id, self.current / other, self.target)


@dataclass
class Duration:
    """
    Processing duration event payload

    Metric emitted on the `DURATION_EVENT` for all components of type `EventDrivenComponent` or `IteratingComponent`
    """

    component_id: str
    """
    :type: str

    `component id <Component.id>` of emitting component
    """

    duration_seconds: float
    """
    Average duration of one processing step (the time the ``process()`` method runs) in seconds
    """

    def __add__(self, other: 'Duration'):
        if self.component_id != other.component_id:
            raise ValueError('Cannot add durations of different components')
        return Duration(self.component_id, self.duration_seconds + other.duration_seconds)

    def __truediv__(self, other: int):
        return Duration(self.component_id, self.duration_seconds / other)
