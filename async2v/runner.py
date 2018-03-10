import asyncio
import queue
import time
from typing import TypeVar, Generic

import logwood

from async2v.components.base import Component, IteratingComponent, EventDrivenComponent, BareComponent
from async2v.error import ConfigurationError
from async2v.fields import Output, DoubleBufferedField

C = TypeVar('C', BareComponent, EventDrivenComponent, IteratingComponent)


def create_component_runner(component: Component, main_queue: queue.Queue):
    if isinstance(component, IteratingComponent):
        _ensure_no_triggering_fields(component)
        return IteratingComponentRunner(component, main_queue)
    elif isinstance(component, EventDrivenComponent):
        _ensure_at_least_one_triggering_field(component)
        return EventDrivenComponentRunner(component, main_queue)
    elif isinstance(component, BareComponent):
        _ensure_no_double_buffered_fields(component)
        return BareComponentRunner(component, main_queue)
    else:
        raise RuntimeError(f'Unknown component type {component.__class__.__name__} of {component.id}')


def _ensure_no_triggering_fields(component):
    triggering_fields = [f for f in vars(component).values() if isinstance(f, DoubleBufferedField) and f.trigger]
    if len(triggering_fields) > 0:
        raise ConfigurationError(f'IteratingComponent {component.id} cannot have trigger fields')


def _ensure_at_least_one_triggering_field(component):
    triggering_fields = [f for f in vars(component).values() if isinstance(f, DoubleBufferedField) and f.trigger]
    if len(triggering_fields) == 0:
        raise ConfigurationError(f'EventDrivenComponent {component.id} must have at least one trigger field')


def _ensure_no_double_buffered_fields(component):
    double_buffered_fields = [f for f in vars(component).values() if isinstance(f, DoubleBufferedField)]
    if len(double_buffered_fields) == 0:
        raise ConfigurationError(f'BareComponent {component.id} cannot have double-buffered fields')


class BaseComponentRunner(Generic[C]):

    def __init__(self, component: C, main_queue: queue.Queue):
        self._component = component  # type: C
        self._stopped = asyncio.Event()
        self.logger = logwood.get_logger(self.__class__.__name__)
        self.duration = Output('async2v.process_duration')
        self.duration.set_queue(main_queue)

    def stop(self):
        self.logger.debug('Stopping component runner {}', self._component.id)
        self._stopped.set()

    async def run(self):
        raise NotImplementedError

    def _publish_duration(self, duration: float) -> None:
        self.duration.push({
            'id': self._component.id,
            'duration_seconds': duration,
        })


class IteratingComponentRunner(BaseComponentRunner[IteratingComponent]):

    def __init__(self, component: IteratingComponent, main_queue: queue.Queue):
        super().__init__(component, main_queue)
        self.fps = Output('async2v.fps')
        self.fps.set_queue(main_queue)
        self._smoothed_fps = 0
        self._fps_last_published = 0

    async def run(self):
        desired_delta = 1 / self._component.target_fps
        input_fields = [f for f in vars(self._component).values() if isinstance(f, DoubleBufferedField)]

        self.logger.debug('Setup component runner {}', self._component.id)
        await self._component.setup()

        start = time.time()
        while not self._stopped.is_set():
            for f in input_fields:
                f.switch()
            await self._component.process()
            duration = time.time() - start
            await asyncio.sleep(desired_delta - duration)
            stop = time.time()
            self._publish_fps(stop - start)
            self._publish_duration(duration)
            start = stop

        self.logger.debug('Cleanup component {}', self._component.id)
        await self._component.cleanup()

    def _publish_fps(self, current_delta: float) -> None:
        self._smoothed_fps = (self._smoothed_fps + 1 / current_delta) / 2
        now = time.time()
        if now - self._fps_last_published > 1:
            self.fps.push({
                'id': self._component.id,
                'current': self._smoothed_fps,
                'target': self._component.target_fps,
            })
            self._fps_last_published = now


class EventDrivenComponentRunner(BaseComponentRunner[EventDrivenComponent]):

    def __init__(self, component: EventDrivenComponent, main_queue: queue.Queue):
        super().__init__(component, main_queue)
        self._trigger = asyncio.Event()

    def trigger(self):
        self._trigger.set()

    async def run(self):
        input_fields = [f for f in vars(self._component).values() if isinstance(f, DoubleBufferedField)]

        self.logger.debug('Setup component runner {}', self._component.id)
        await self._component.setup()

        while not self._stopped.is_set():
            try:
                await asyncio.wait_for(self._trigger.wait(), timeout=0.1)
            except asyncio.TimeoutError:
                continue
            start = time.time()
            for f in input_fields:
                f.switch()
            self._trigger.clear()
            await self._component.process()
            duration = time.time() - start
            self._publish_duration(duration)

        self.logger.debug('Cleanup component {}', self._component.id)
        await self._component.cleanup()


class BareComponentRunner(BaseComponentRunner[BareComponent]):

    async def run(self):
        self.logger.debug('Setup component runner {}', self._component.id)
        await self._component.setup()
        await self._stopped.wait()
        self.logger.debug('Cleanup component {}', self._component.id)
        await self._component.cleanup()
