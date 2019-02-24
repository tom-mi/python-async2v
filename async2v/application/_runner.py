import asyncio
import queue
import time
from typing import TypeVar, Generic

import logwood

from async2v.application._registry import ComponentNode
from async2v.application.metric import Fps, Duration
from async2v.components.base import IteratingComponent, EventDrivenComponent, BareComponent
from async2v.event import Event, FPS_EVENT, DURATION_EVENT, SHUTDOWN_DUE_TO_ERROR
from async2v.fields import DoubleBufferedField, AveragingOutput

C = TypeVar('C', BareComponent, EventDrivenComponent, IteratingComponent)

METRIC_AVERAGING_INTERVAL_SECONDS = 1


def create_component_runner(node: ComponentNode, main_queue: queue.Queue):
    if isinstance(node.component, IteratingComponent):
        return IteratingComponentRunner(node, main_queue)
    elif isinstance(node.component, EventDrivenComponent):
        return EventDrivenComponentRunner(node, main_queue)
    elif isinstance(node.component, BareComponent):
        return BareComponentRunner(node, main_queue)
    else:
        raise RuntimeError(f'Unknown component type {node.component.__class__.__name__} of {node.id}')


class BaseComponentRunner(Generic[C]):

    def __init__(self, node: ComponentNode, main_queue: queue.Queue):
        self._node = node
        self._component = node.component  # type: C
        self._stopped = asyncio.Event()
        self._queue = main_queue
        self.logger = logwood.get_logger(self.__class__.__name__)
        self.duration = AveragingOutput(DURATION_EVENT, interval=METRIC_AVERAGING_INTERVAL_SECONDS)
        self.duration.set_queue(main_queue)

    def stop(self):
        self.logger.debug('Stopping component runner {}', self._node.id)
        self._stopped.set()

    async def run(self):
        raise NotImplementedError

    def _publish_duration(self, duration: float) -> None:
        self.duration.push(Duration(self._component.id, duration))


class IteratingComponentRunner(BaseComponentRunner):

    def __init__(self, node: ComponentNode, main_queue: queue.Queue):
        super().__init__(node, main_queue)
        self.fps = AveragingOutput(FPS_EVENT, interval=METRIC_AVERAGING_INTERVAL_SECONDS)
        self.fps.set_queue(main_queue)
        self._smoothed_fps = 0
        self._fps_last_published = 0

    async def run(self):
        desired_delta = 1 / self._component.target_fps
        input_fields = [f.field for f in self._node.all_inputs if isinstance(f.field, DoubleBufferedField)]

        self.logger.debug('Setup component runner {}', self._component.id)
        await self._component.setup()

        start = time.time()
        while not self._stopped.is_set():
            for f in input_fields:
                f.switch()

            # noinspection PyBroadException
            try:
                await self._component.process()
            except Exception:
                self.logger.exception('Unexpected error')
                self._queue.put(Event(SHUTDOWN_DUE_TO_ERROR))

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
        self.fps.push(Fps(self._component.id, self._smoothed_fps, self._component.target_fps))


class EventDrivenComponentRunner(BaseComponentRunner[EventDrivenComponent]):

    def __init__(self, node: ComponentNode, main_queue: queue.Queue):
        super().__init__(node, main_queue)
        self._trigger = asyncio.Event()

    def trigger(self):
        self._trigger.set()

    async def run(self):
        input_fields = [f.field for f in self._node.all_inputs if isinstance(f.field, DoubleBufferedField)]

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

            # noinspection PyBroadException
            try:
                await self._component.process()
            except Exception:
                self.logger.exception('Unexpected error')
                self._queue.put(Event(SHUTDOWN_DUE_TO_ERROR))

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
