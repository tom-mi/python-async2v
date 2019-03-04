#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK
import cv2

from async2v.application import Application
from async2v.cli import ApplicationLauncher
from async2v.components.base import EventDrivenComponent
from async2v.components.opencv.video import VideoSource, Frame
from async2v.components.pygame.display import OpenCvDebugDisplay
from async2v.components.pygame.main import MainWindow
from async2v.event import OPENCV_FRAME_EVENT
from async2v.fields import Latest, Output


class FlipFilter(EventDrivenComponent):

    def __init__(self):
        self.input: Latest[Frame] = Latest(key='source', trigger=True)
        self.debug_output: Output[Frame] = Output(key=OPENCV_FRAME_EVENT)

    async def process(self) -> None:
        flipped_image = cv2.flip(self.input.value.image, 1)
        self.debug_output.push(Frame(flipped_image, source=self.id))


class Launcher(ApplicationLauncher):

    def __init__(self):
        super().__init__()
        self.add_configurator(MainWindow.configurator())
        self.add_configurator(VideoSource.configurator())

    def register_application_components(self, args, app: Application):
        displays = [
            OpenCvDebugDisplay(),
        ]
        main_window = MainWindow(displays, config=MainWindow.configurator().config_from_args(args))
        video_source = VideoSource(config=VideoSource.configurator().config_from_args(args))
        flip_filter = FlipFilter()
        app.register(main_window, video_source, flip_filter)


def main():
    Launcher().main()


if __name__ == '__main__':
    main()
