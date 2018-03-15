import asyncio
import queue
import time
from threading import Thread
from typing import Dict, List

import logwood

from async2v.components.base import Component, IteratingComponent
from async2v.event import REGISTER_EVENT, SHUTDOWN_EVENT, Event, DEREGISTER_EVENT
from async2v.graph import ApplicationGraph
from async2v.runner import create_component_runner, BaseComponentRunner

DRAIN_TIMEOUT_SECONDS = 5
DRAIN_QUIET_PERIOD_SECONDS = 1
TASK_SHUTDOWN_TIMEOUT_SECONDS = 5


class Application(Thread):

    def __init__(self):
        super().__init__()
        self.logger = logwood.get_logger(self.__class__.__name__)
        self.graph = ApplicationGraph()
        self._queue = queue.Queue()  # type: queue.Queue
        self._last_read_from_queue = 0  # type: float
        self._component_runners = {}  # type: Dict[Component, BaseComponentRunner]
        self._component_runner_tasks = {}  # type: Dict[Component, asyncio.Task]
        self._internal_tasks = []  # type: List[asyncio.Task]
        self._loop = asyncio.new_event_loop()  # type: asyncio.AbstractEventLoop
        self._internal_tasks_stopped = asyncio.Event(loop=self._loop)
        self._main_loop_stopped = asyncio.Event(loop=self._loop)
        self._main_loop_task = None  # type: asyncio.Task

    def stop(self):
        self._queue.put(Event(SHUTDOWN_EVENT))
        self.join()

    def register(self, *components: Component) -> None:
        if self.is_alive():
            for component in components:
                self._queue.put(Event(REGISTER_EVENT, component))
        else:
            for component in components:
                self._do_register(component)

    def deregister(self, *components: Component) -> None:
        if self.is_alive():
            for component in components:
                self._queue.put(Event(DEREGISTER_EVENT, component))
        else:
            for component in components:
                self._do_deregister(component)

    def run(self):
        asyncio.set_event_loop(self._loop)

        self._internal_tasks = [
            self._create_task_with_error_handler(self._handle_events(), self.logger),
        ]

        for component in self.graph.components():
            if component not in self._component_runners:
                self._start_component_runner(component)

        self._main_loop_task = self._loop.create_task(self._main_loop())
        self._loop.run_until_complete(self._main_loop_task)

    async def _main_loop(self):
        await self._main_loop_stopped.wait()

    async def _handle_events(self):
        while not self._internal_tasks_stopped.is_set():
            # noinspection PyBroadException
            try:
                event = await self._loop.run_in_executor(None, lambda: self._queue.get(timeout=0.1))  # type: Event
                self._last_read_from_queue = time.time()
                if event.key == SHUTDOWN_EVENT:
                    self._create_task_with_error_handler(self._shutdown(), self.logger)
                elif event.key == REGISTER_EVENT:
                    self._do_register(event.value)
                    self._start_component_runner(event.value)
                elif event.key == DEREGISTER_EVENT:
                    self._do_deregister(event.value)
                    self._stop_component_runner(event.value)
                for field in self.graph.inputs_by_key(event.key):
                    field.set(event)
                for component in self.graph.triggered_component_by_key(event.key):
                    runner = self._component_runners[component]
                    # noinspection PyUnresolvedReferences
                    runner.trigger()

            except queue.Empty:
                pass
            except Exception:
                self.logger.exception('Unexpected error')
                await self._shutdown()

    def _do_register(self, component: Component) -> None:
        self.logger.info('Registering {}', component.id)
        self.graph.register(component)
        self._connect_output_queue(component)

    def _connect_output_queue(self, component: Component):
        for field in self.graph.node_by_component(component).all_outputs.values():
            field.set_queue(self._queue)

    def _start_component_runner(self, component: Component) -> None:
        self.logger.debug('Starting component runner for component {}', component.id)
        if component in self._component_runners:
            raise ValueError(f'Component {component} already has a runner')
        node = self.graph.node_by_component(component)
        runner = create_component_runner(node, self._queue)
        self._component_runners[component] = runner
        task = self._create_task_with_error_handler(runner.run(), component.logger)
        self._component_runner_tasks[component] = task

    def _do_deregister(self, component: Component) -> None:
        self.logger.info('De-registering {}', component.id)
        self.graph.deregister(component)

    def _stop_component_runner(self, component: Component) -> None:
        if component not in self._component_runners:
            raise ValueError(f'Component {component} does not have a runner')
        runner = self._component_runners.pop(component)
        runner.stop()

    async def _shutdown(self):
        self.logger.info('Initiating shutdown')

        self.logger.debug('Shutting down iterating components')
        for component, runner in self._component_runners.items():
            if isinstance(component, IteratingComponent):
                runner.stop()

        self.logger.debug('Draining event queue')
        drain_start = time.time()
        while not (self._queue.qsize() == 0 and time.time() - self._last_read_from_queue > DRAIN_QUIET_PERIOD_SECONDS):
            if time.time() - drain_start > DRAIN_TIMEOUT_SECONDS:
                self.logger.warning(f'Could not drain event queue within {DRAIN_TIMEOUT_SECONDS} seconds')
                break
            await asyncio.sleep(0.1)

        self.logger.debug('Shutting down remaining components')
        for component, runner in self._component_runners.items():
            if not isinstance(component, IteratingComponent):
                runner.stop()

        for component, task in self._component_runner_tasks.items():
            # noinspection PyBroadException
            try:
                await asyncio.wait_for(task, timeout=5)
            except asyncio.TimeoutError:
                self.logger.error('Component {} did not stop gracefully', component.id)
            except Exception:
                # These exception should already have been handled in error handler
                pass

        self.logger.debug('Stopping internal tasks')
        self._internal_tasks_stopped.set()

        for task in self._internal_tasks:
            # noinspection PyBroadException
            try:
                await asyncio.wait_for(task, timeout=5)
            except asyncio.TimeoutError:
                self.logger.error('Task {} did not stop gracefully', task)
            except Exception:
                # These exception should already have been handled in error handler
                pass

        self.logger.info('Shutdown complete')
        self._main_loop_stopped.set()

    def _create_task_with_error_handler(self, coro, logger: logwood.Logger):
        task = self._loop.create_task(coro)
        task.add_done_callback(self._error_handling_done_callback(logger))
        return task

    def _error_handling_done_callback(self, logger: logwood.Logger):
        def callback(future):
            # noinspection PyBroadException
            try:
                future.result()
            except asyncio.CancelledError:
                logger.warning('Task was cancelled')
            except Exception:
                logger.exception(f'Unexpected error')
                self._queue.put(Event(SHUTDOWN_EVENT))

        return callback
