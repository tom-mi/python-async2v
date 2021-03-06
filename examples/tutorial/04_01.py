#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK
import cv2

from async2v.application import Application
from async2v.cli import ApplicationLauncher
from async2v.components.base import EventDrivenComponent
from async2v.components.opencv.video import VideoSource, Frame
from async2v.components.pygame.display import OpenCvDebugDisplay, OpenCvDisplay
from async2v.components.pygame.keyboard import EventBasedKeyboardHandler, Action
from async2v.components.pygame.main import MainWindow
from async2v.event import OPENCV_FRAME_EVENT
from async2v.fields import Latest, Output


class FlipFilter(EventDrivenComponent):

    def __init__(self, input_key: str, output_key: str):
        self.input: Latest[Frame] = Latest(key=input_key, trigger=True)
        self.output: Output[Frame] = Output(key=output_key)
        self.debug_output: Output[Frame] = Output(key=OPENCV_FRAME_EVENT)

    async def process(self) -> None:
        flipped_image = cv2.flip(self.input.value.image, 1)
        output_frame = Frame(flipped_image, source=self.id)
        self.output.push(output_frame)
        self.debug_output.push(output_frame)


class MyKeyboardHandler(EventBasedKeyboardHandler):
    ACTIONS = [
        Action('toggle_horizontal_flip', ['LEFT', 'RIGHT'], 'Toggle horizontal flip'),
        Action('toggle_vertical_flip', ['UP', 'DOWN'], 'Toggle vertical flip'),
    ]


class Launcher(ApplicationLauncher):

    def __init__(self):
        super().__init__()
        self.add_configurator(MainWindow.configurator())
        self.add_configurator(VideoSource.configurator())
        self.add_configurator(MyKeyboardHandler.configurator())

    def register_application_components(self, args, app: Application):
        displays = [
            OpenCvDisplay('flipped'),
            OpenCvDebugDisplay(),
        ]
        keyboard_handler = MyKeyboardHandler(layout=MyKeyboardHandler.configurator().layout_from_args(args))
        main_window = MainWindow(displays, config=MainWindow.configurator().config_from_args(args),
                                 keyboard_handler=keyboard_handler)
        video_source = VideoSource(config=VideoSource.configurator().config_from_args(args))
        flip_filter = FlipFilter('source', 'flipped')
        app.register(main_window, video_source, flip_filter)


def main():
    Launcher().main()


if __name__ == '__main__':
    main()
