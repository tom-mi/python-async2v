import asyncio
import queue
from threading import Thread
from typing import Dict

import logwood

from async2v.components.base import Component
from async2v.event import REGISTER_EVENT, SHUTDOWN_EVENT, Event, DEREGISTER_EVENT
from async2v.fields import Output
from async2v.graph import ApplicationGraph
from async2v.runner import create_component_runner, BaseComponentRunner


class Application(Thread):

    def __init__(self):
        super().__init__()
        self.logger = logwood.get_logger(self.__class__.__name__)
        self._graph = ApplicationGraph()
        self._queue = queue.Queue()  # type: queue.Queue
        self._component_runners = {}  # type: Dict[Component, BaseComponentRunner]
        self._component_runner_tasks = {}  # type: Dict[Component, asyncio.Task]
        self._loop = asyncio.new_event_loop()  # type: asyncio.AbstractEventLoop
        self._stopped = asyncio.Event(loop=self._loop)

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
        internal_tasks = [
            self._loop.create_task(self._handle_events())
        ]

        for task in internal_tasks:
            task.add_done_callback(self._error_handling_done_callback(self.logger))

        for component in self._graph.components():
            if component not in self._component_runners:
                self._start_component_runner(component)

        self._loop.run_until_complete(self._loop.create_task(self._main_loop()))

    async def _main_loop(self):
        await self._stopped.wait()

    async def _handle_events(self):
        while not self._stopped.is_set():
            # noinspection PyBroadException
            try:
                event = await self._loop.run_in_executor(None, lambda: self._queue.get(timeout=0.1))  # type: Event
                if event.key == SHUTDOWN_EVENT:
                    await self._shutdown()
                elif event.key == REGISTER_EVENT:
                    self._do_register(event.value)
                    self._start_component_runner(event.value)
                elif event.key == DEREGISTER_EVENT:
                    self._do_deregister(event.value)
                    self._stop_component_runner(event.value)
                for field in self._graph.inputs_by_key(event.key):
                    field.set(event)
                for component in self._graph.triggered_component_by_key(event.key):
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
        self._graph.register(component)
        self._connect_output_queue(component)

    def _connect_output_queue(self, component: Component):
        for field in vars(component).values():
            if isinstance(field, Output):
                field.set_queue(self._queue)

    def _start_component_runner(self, component: Component) -> None:
        self.logger.debug('Starting component runner for component {}', component.id)
        if component in self._component_runners:
            raise ValueError(f'Component {component} already has a runner')
        runner = create_component_runner(component, self._queue)
        self._component_runners[component] = runner
        task = self._loop.create_task(runner.run())
        task.add_done_callback(self._error_handling_done_callback(component.logger))
        self._component_runner_tasks[component] = task

    def _do_deregister(self, component: Component) -> None:
        self.logger.info('De-registering {}', component.id)
        self._graph.deregister(component)

    def _stop_component_runner(self, component: Component) -> None:
        if component not in self._component_runners:
            raise ValueError(f'Component {component} does not have a runner')
        runner = self._component_runners.pop(component)
        runner.stop()

    async def _shutdown(self):
        self.logger.info('Initiating shutdown')
        for runner in self._component_runners.values():
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
        self._stopped.set()
        self.logger.info('Shutdown complete')

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
