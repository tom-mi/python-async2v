import asyncio
import queue
import threading
import time
from typing import Dict, List

import logwood

from async2v.components.base import Component, IteratingComponent
from async2v.event import REGISTER_EVENT, SHUTDOWN_EVENT, Event, DEREGISTER_EVENT, SHUTDOWN_DUE_TO_ERROR
from ._registry import Registry
from ._runner import create_component_runner, BaseComponentRunner

DRAIN_TIMEOUT_SECONDS = 5
DRAIN_QUIET_PERIOD_SECONDS = 1
TASK_SHUTDOWN_TIMEOUT_SECONDS = 5


class Application(threading.Thread):
    """
    Manages the lifecycle of an async2v application at construction and runtime

    Usually you want to use an `ApplicationLauncher` instead of instantiating an `Application` instance by hand.

    .. method:: start()

        Start the application.
    """

    def __init__(self):
        super().__init__()
        self.logger = logwood.get_logger(self.__class__.__name__)
        self._registry = Registry()
        self._queue: queue.Queue = queue.Queue()
        self._last_read_from_queue: float = 0
        self._component_runners: Dict[Component, BaseComponentRunner] = {}
        self._component_runner_tasks: Dict[Component, asyncio.Task] = {}
        self._internal_tasks: List[asyncio.Task] = []
        self._loop: asyncio.AbstractEventLoop = asyncio.new_event_loop()
        self._internal_tasks_stopped = asyncio.Event(loop=self._loop)
        self._main_loop_stopped = asyncio.Event(loop=self._loop)
        self._main_loop_task: asyncio.Task = None
        self._has_error_occurred = threading.Event()
        self._shutting_down = threading.Event()

    def register(self, *components: Component) -> None:
        """
        Register one or more components to the application.

        * When called before the application has been started, the given components are added immediately.
          They will be started upon application startup.
        * When called on a running application, a registration request is put on the main event queue and will be
          processed asynchronously within the main event loop. The components will be started immediately after the
          registration is complete.

        :param components:
        """
        if self.is_alive():
            for component in components:
                self._queue.put(Event(REGISTER_EVENT, component))
        else:
            for component in components:
                self._do_register(component)

    def deregister(self, *components: Component) -> None:
        """
        Deregister one or more components from the application.

        * When called before the application has been started, the given components are removed immediately.
        * When called on a running application, a deregistration request is put on the event queue and will be
          processed asynchronously within the main event loop. The components will be stopped before the
          deregistration.

        :param components:
        """
        if self.is_alive():
            for component in components:
                self._queue.put(Event(DEREGISTER_EVENT, component))
        else:
            for component in components:
                self._do_deregister(component)

    def stop(self) -> None:
        """
        Stop the application.

        The application is stopped by putting a shutdown request on the event queue. This method waits for the
        underlying thread to finish, hence can be deemed synchronous.
        """
        self._queue.put(Event(SHUTDOWN_EVENT))
        self.join()

    def has_error_occurred(self) -> bool:
        """
        Returns `True` if the application has been shut down or is being shut down due to an uncaught Exception in
        one of the components.
        """
        return self._has_error_occurred.is_set()

    def run(self) -> None:
        """
        Implementation of the application thread. Don't call this method directly, use :py:func:`start` instead.
        """
        asyncio.set_event_loop(self._loop)

        self._internal_tasks = [
            self._create_task_with_error_handler(self._handle_events(), self.logger),
        ]

        for component in self._registry.components():
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
                while event is not None:
                    self._last_read_from_queue = time.time()
                    self._handle_event(event)
                    event = self._queue.get_nowait()
            except queue.Empty:
                pass
            except Exception:
                self.logger.exception('Unexpected error')
                self._has_error_occurred.set()
                await self._shutdown()

    def _handle_event(self, event: Event):
        if event.key == SHUTDOWN_EVENT:
            self._create_task_with_error_handler(self._shutdown(), self.logger)
        if event.key == SHUTDOWN_DUE_TO_ERROR:
            self._has_error_occurred.set()
            self._create_task_with_error_handler(self._shutdown(), self.logger)
        elif event.key == REGISTER_EVENT:
            self._do_register(event.value)
            self._start_component_runner(event.value)
        elif event.key == DEREGISTER_EVENT:
            self._do_deregister(event.value)
            self._stop_component_runner(event.value)
        for field in self._registry.inputs_by_key(event.key):
            field.set(event)
        for component in self._registry.triggered_component_by_key(event.key):
            runner = self._component_runners[component]
            # noinspection PyUnresolvedReferences
            runner.trigger()

    def _do_register(self, component: Component) -> None:
        self.logger.info('Registering {}', component.id)
        self._registry.register(component)
        self._connect_output_queue(component)

    def _connect_output_queue(self, component: Component):
        for field_node in self._registry.node_by_component(component).all_outputs:
            field_node.field.set_queue(self._queue)

    def _start_component_runner(self, component: Component) -> None:
        self.logger.debug('Starting component runner for component {}', component.id)
        if component in self._component_runners:
            raise ValueError(f'Component {component} already has a runner')
        node = self._registry.node_by_component(component)
        runner = create_component_runner(node, self._queue)
        self._component_runners[component] = runner
        task = self._create_task_with_error_handler(runner.run(), component.logger)
        self._component_runner_tasks[component] = task

    def _do_deregister(self, component: Component) -> None:
        self.logger.info('De-registering {}', component.id)
        self._registry.deregister(component)

    def _stop_component_runner(self, component: Component) -> None:
        if component not in self._component_runners:
            raise ValueError(f'Component {component} does not have a runner')
        runner = self._component_runners.pop(component)
        runner.stop()

    async def _shutdown(self):
        if self._shutting_down.is_set():
            return
        self._shutting_down.set()
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
                self._queue.put(Event(SHUTDOWN_DUE_TO_ERROR))

        return callback
