#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK
import asyncio
from typing import NamedTuple, List

import cv2

from async2v import event
from async2v.application import Application
from async2v.cli import ApplicationLauncher
from async2v.components.base import EventDrivenComponent
from async2v.components.opencv.video import VideoSource, Frame
from async2v.components.pygame.display import OpenCvDebugDisplay, OpenCvDisplay
from async2v.components.pygame.main import _MainWindowConfigurator, MainWindow
from async2v.components.pygame.mouse import EventBasedMouseHandler, MouseEvent, MouseMovement
from async2v.fields import Latest, Output, Buffer, LatestBy


class Person(NamedTuple):
    x: int
    y: int
    w: int
    h: int
    weight: float


class PersonDetector(EventDrivenComponent):

    def __init__(self):
        self.source = Latest('source', trigger=True)  # type: Latest[Frame]
        self._hog = cv2.HOGDescriptor()
        self._hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
        self.output = Output('people')

    async def process(self):
        rects, weights = await asyncio.get_event_loop().run_in_executor(None, self._detect)
        people = [Person(*rect, weight) for rect, weight in zip(rects, weights)]
        self.output.push(people)

    def _detect(self):
        step_size = int(self.source.value.width / 200)
        scale = 1.5
        padding = 16
        return self._hog.detectMultiScale(self.source.value.image, winStride=(step_size, step_size),
                                          scale=scale, padding=(padding, padding), useMeanshiftGrouping=True)


class PersonDisplay(EventDrivenComponent):
    RECT_COLOR = (255, 0, 0)
    HIGHLIGHTED_RECT_COLOR = (255, 255, 0)
    RECT_THICKNESS = 2

    def __init__(self):
        self.source = Latest('source', trigger=True)  # type: Latest[Frame]
        self.people = Latest('people')  # type: Latest[List[Person]]
        self.output = Output('display')
        self.debug = Output(event.OPENCV_FRAME_EVENT)
        self.mouse = Buffer(EventBasedMouseHandler.MOUSE_EVENT)  # type: Buffer[MouseEvent]
        self.mouse_move = LatestBy(EventBasedMouseHandler.MOUSE_MOVEMENT,
                                   lambda m: m.region.name)  # type: LatestBy[MouseMovement]

    async def process(self):
        image = self.source.value.image.copy()

        if self.people.value:
            for p in self.people.value:
                if self._contains_mouse_pointer(p):
                    color = self.HIGHLIGHTED_RECT_COLOR
                else:
                    color = self.RECT_COLOR
                cv2.rectangle(image, (p.x, p.y), (p.x + p.w, p.y + p.h), color, self.RECT_THICKNESS)

        frame = Frame(image, 'display')
        self.output.push(frame)
        self.debug.push(frame)

    def _contains_mouse_pointer(self, person: Person) -> bool:
        if not self.mouse_move.value_dict.get('display', None):
            return False
        x, y = self.mouse_move.value_dict['display'].restored_position
        return person.x <= x <= person.x + person.w and person.y <= y <= person.y + person.h


class Launcher(ApplicationLauncher):

    def __init__(self):
        super().__init__()
        self.add_configurator(_MainWindowConfigurator())
        self.add_configurator(VideoSource.configurator())

    def register_application_components(self, args, app: Application):
        source = VideoSource(VideoSource.configurator().config_from_args(args))
        person_detector = PersonDetector()
        person_display = PersonDisplay()
        displays = [
            OpenCvDisplay('display'),
            OpenCvDebugDisplay(),
        ]
        mouse_handler = EventBasedMouseHandler()
        main_window_config = _MainWindowConfigurator.config_from_args(args)
        main_window = MainWindow(displays, mouse_handler=mouse_handler, config=main_window_config)
        app.register(source, person_detector, person_display, main_window)


if __name__ == '__main__':
    Launcher().main()
