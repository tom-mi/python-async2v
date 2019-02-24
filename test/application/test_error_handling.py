import pytest

from async2v.components.base import IteratingComponent, EventDrivenComponent
from async2v.event import Event
from async2v.fields import Latest, Output, T


class TriggerComponent(IteratingComponent):

    def __init__(self) -> None:
        super().__init__()
        self.output = Output('trigger')

    @property
    def target_fps(self) -> int:
        return 1

    async def process(self) -> None:
        self.output.push(None)


class ErroneousIteratingComponent(IteratingComponent):
    @property
    def target_fps(self) -> int:
        return 10

    async def process(self) -> None:
        raise Exception("broken")


class ErroneousEventDrivenComponent(EventDrivenComponent):

    def __init__(self) -> None:
        super().__init__()
        self.trigger = Latest('trigger', trigger=True)

    async def process(self) -> None:
        raise Exception("broken")


class BrokenLatest(Latest):

    def set(self, new: Event[T]) -> None:
        super().set(new)
        raise Exception("broken")


class ErroneousFieldComponent(EventDrivenComponent):

    def __init__(self) -> None:
        super().__init__()
        self.trigger = BrokenLatest('trigger', trigger=True)

    async def process(self) -> None:
        pass


class ErroneousSetupComponent(IteratingComponent):

    @property
    def target_fps(self) -> int:
        return 10

    async def process(self) -> None:
        pass

    async def setup(self) -> None:
        raise Exception("broken")


class ErroneousShutdownComponent(IteratingComponent):

    @property
    def target_fps(self) -> int:
        return 10

    async def process(self) -> None:
        self.shutdown()

    async def cleanup(self) -> None:
        raise Exception("broken")


@pytest.mark.parametrize('component', [
    ErroneousEventDrivenComponent,
    ErroneousFieldComponent,
    ErroneousIteratingComponent,
    ErroneousSetupComponent,
    ErroneousShutdownComponent,
])
def test_uncaught_error_in_component_stops_app(app, component):
    app.register(TriggerComponent(), component())
    app.start()
    app.join(20)

    assert not app.is_alive()
    assert app.has_error_occurred()


def test_graceful_shutdown(app):
    app.register(TriggerComponent())
    app.start()
    app.stop()

    assert not app.is_alive()
    assert not app.has_error_occurred()
