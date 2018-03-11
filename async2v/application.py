import asyncio
import queue
from threading import Thread
from typing import List, Dict

import logwood

from async2v.components.base import Component
from async2v.event import REGISTER_EVENT, SHUTDOWN_EVENT, Event
from async2v.fields import DoubleBufferedField, Output, InputField
from async2v.runner import create_component_runner, BaseComponentRunner, EventDrivenComponentRunner


class Application(Thread):

    def __init__(self):
        super().__init__()
        self.logger = logwood.get_logger(self.__class__.__name__)
        self._components = []  # type: [Component]
        self._fields = {}  # type: Dict[str, List[InputField]]
        self._outputs = []  # type: [Output]
        self._queue = queue.Queue()  # type: queue.Queue
        self._component_runners = {}  # type: Dict[Component, BaseComponentRunner]
        self._component_runner_tasks = {}  # type: Dict[Component, asyncio.Task]
        self._runners_by_triggering_fields = {}  # type: Dict[str, List[EventDrivenComponentRunner]]
        self._loop = asyncio.new_event_loop()  # type: asyncio.AbstractEventLoop
        self._stopped = asyncio.Event(loop=self._loop)

    def stop(self):
        self._queue.put(Event(SHUTDOWN_EVENT))
        self.join()

    def register(self, *components: Component) -> None:
        for component in components:
            self._queue.put(Event(REGISTER_EVENT, component))

    def run(self):
        asyncio.set_event_loop(self._loop)
        internal_tasks = [
            self._loop.create_task(self._handle_events())
        ]

        for task in internal_tasks:
            task.add_done_callback(self._error_handling_done_callback(self.logger))

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
                for field in self._fields.get(event.key, []):
                    field.set(event)
                for runner in self._runners_by_triggering_fields.get(event.key, []):
                    runner.trigger()

            except queue.Empty:
                pass
            except Exception:
                self.logger.exception('Unexpected error')
                self._shutdown()

    def _do_register(self, component: Component) -> None:
        self.logger.info('Registering {}', component.id)
        if component in self._components:
            raise ValueError(f'Component {component} is already registered')
        self._components.append(component)
        self._register_fields(component)
        self._start_component_runner(component)

    def _register_fields(self, component: Component) -> None:
        for field in vars(component).values():
            if isinstance(field, InputField):
                if field.key not in self._fields:
                    self._fields[field.key] = []
                self._fields[field.key].append(field)

            elif isinstance(field, Output):
                self._outputs.append(field)
                field.set_queue(self._queue)

    def _start_component_runner(self, component: Component) -> None:
        self.logger.debug('Starting component runner for component {}', component.id)
        runner = create_component_runner(component, self._queue)
        if isinstance(runner, EventDrivenComponentRunner):
            self._register_events(runner, component)
        self._component_runners[component] = runner
        task = self._loop.create_task(runner.run())
        task.add_done_callback(self._error_handling_done_callback(component.logger))
        self._component_runner_tasks[component] = task

    def _register_events(self, runner: EventDrivenComponentRunner, component: Component):
        for field in vars(component).values():
            if isinstance(field, DoubleBufferedField):
                if field.key not in self._runners_by_triggering_fields:
                    self._runners_by_triggering_fields[field.key] = []
                self._runners_by_triggering_fields[field.key].append(runner)

    def _do_deregister(self, component: Component) -> None:
        if component not in self._components:
            raise ValueError(f'Component {component} is not registered')
        runner = self._component_runners.pop(component)
        runner.stop()
        self._components.remove(component)
        self._deregister_fields(component)
        if isinstance(runner, EventDrivenComponentRunner):
            self._deregister_events(runner, component)

    def _deregister_fields(self, component: Component) -> None:
        for key, value in vars(component).items():
            if isinstance(value, InputField):
                self._fields[key].remove(value)
                if len(self._fields[key]) == 0:
                    del self._fields[key]
            elif isinstance(value, Output):
                self._outputs.remove(value)
                value.set_queue(None)

    def _deregister_events(self, runner: EventDrivenComponentRunner, component: Component):
        for field in vars(component).values():
            if isinstance(field, DoubleBufferedField):
                self._runners_by_triggering_fields[field.key].remove(runner)
                if len(self._runners_by_triggering_fields[field.key]):
                    del self._runners_by_triggering_fields[field.key]

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
