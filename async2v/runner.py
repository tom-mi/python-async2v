import asyncio
import queue
import time

import logwood

from async2v.components.base import Component
from async2v.fields import Output, DoubleBufferedField


class ComponentRunner:

    def __init__(self, component: Component, queue: queue.Queue):
        self._component = component
        self._stopped = asyncio.Event()
        self.fps = Output('async2v.fps')
        self.fps._set_queue(queue)
        self._smoothed_fps = 0
        self._fps_last_published = 0
        self._task = None  # type: asyncio.Task
        self.logger = logwood.get_logger(self.__class__.__name__)

    def stop(self):
        self.logger.debug('Stopping component runner {}', self._component.id)
        self._stopped.set()

    async def run(self):
        desired_delta = 1 / self._component.target_fps
        input_fields = [f for f in vars(self._component).values() if isinstance(f, DoubleBufferedField)]

        self.logger.debug('Setup component runner {}', self._component.id)
        self._component.setup()

        start = time.time()
        while not self._stopped.is_set():
            for f in input_fields:
                f._switch()
            await self._component.process()
            current_delta = time.time() - start
            await asyncio.sleep(desired_delta - current_delta)
            stop = time.time()
            self._publish_fps(stop - start)
            start = stop

        self.logger.debug('Cleanup component {}', self._component.id)
        self._component.cleanup()

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