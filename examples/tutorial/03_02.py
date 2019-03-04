#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK
import cv2

from async2v.application import Application
from async2v.cli import ApplicationLauncher
from async2v.components.base import EventDrivenComponent
from async2v.components.opencv.video import VideoSource, Frame
from async2v.components.pygame.display import OpenCvDebugDisplay, OpenCvDisplay
from async2v.components.pygame.main import MainWindow
from async2v.event import OPENCV_FRAME_EVENT
from async2v.fields import Latest, Output
from async2v.util import run_in_executor


class PersonDetectFilter(EventDrivenComponent):

    def __init__(self, input_key: str, output_key: str):
        self.input: Latest[Frame] = Latest(key=input_key, trigger=True)
        self.output: Output[Frame] = Output(key=output_key)
        self.debug_output: Output[Frame] = Output(key=OPENCV_FRAME_EVENT)
        self.hog = cv2.HOGDescriptor()
        self.hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())

    async def process(self) -> None:
        people, weights = await run_in_executor(self.detect, self.input.value.image)
        output_image = self.input.value.image.copy()
        for (x, y, w, h) in people:
            cv2.rectangle(output_image, (x, y), (x + w, y + h), (255, 255, 255), 2)
        output_frame = Frame(output_image, source=self.id)
        self.output.push(output_frame)
        self.debug_output.push(output_frame)

    def detect(self, image):
        return self.hog.detectMultiScale(image, scale=1.01)


class Launcher(ApplicationLauncher):

    def __init__(self):
        super().__init__()
        self.add_configurator(MainWindow.configurator())
        self.add_configurator(VideoSource.configurator())

    def register_application_components(self, args, app: Application):
        displays = [
            OpenCvDisplay('drawn_people'),
            OpenCvDebugDisplay(),
        ]
        main_window = MainWindow(displays, config=MainWindow.configurator().config_from_args(args))
        video_source = VideoSource(config=VideoSource.configurator().config_from_args(args))
        person_detect_filter = PersonDetectFilter('source', 'drawn_people')
        app.register(main_window, video_source, person_detect_filter)


def main():
    Launcher().main()


if __name__ == '__main__':
    main()
