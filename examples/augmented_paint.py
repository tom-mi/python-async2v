#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK

import cv2
import numpy as np

from async2v import event
from async2v.application import Application
from async2v.cli import ApplicationLauncher
from async2v.components.base import EventDrivenComponent
from async2v.components.opencv.projector import ProjectorDriver2d
from async2v.components.opencv.video import VideoSource, Frame
from async2v.components.pygame.display import OpenCvDebugDisplay, AuxiliaryOpenCvDisplay, OpenCvDisplay
from async2v.components.pygame.main import MainWindow
from async2v.components.pygame.mouse import EventBasedMouseHandler, MouseMovement, MouseEvent, MouseEventType, \
    MouseButton
from async2v.fields import Latest, Output, Buffer


class PaintController(EventDrivenComponent):
    COLOR = (0, 255, 0)
    THICKNESS = 4

    def __init__(self):
        self.source = Latest('source', trigger=True)  # type: Latest[Frame]
        self.output = Output('display')
        self.overlay = Output('overlay')
        self.mouse_movement = Buffer(EventBasedMouseHandler.MOUSE_MOVEMENT, trigger=True)  # type: Buffer[MouseMovement]
        self.mouse_event = Buffer(EventBasedMouseHandler.MOUSE_EVENT, trigger=True)  # type: Buffer[MouseEvent]
        self.debug = Output(event.OPENCV_FRAME_EVENT)
        self.reset_calibration = Output(ProjectorDriver2d.RESET_CALIBRATION_TRIGGER)
        self._canvas = None
        self._last_position = None

    async def process(self):
        if not self.source.value:
            return

        for e in self.mouse_event.values:
            if e.event_type == MouseEventType.DOWN and e.button == MouseButton.RIGHT:
                self._canvas = None
            elif e.event_type == MouseEventType.DOWN and e.button == MouseButton.MIDDLE:
                self.reset_calibration.push(None)

        if self._canvas is None:
            self._canvas = np.zeros(self.source.value.image.shape, dtype='uint8')

        for e in self.mouse_movement.values:
            if e.region.name in ['display', 'VideoSource0'] and e.buttons[MouseButton.LEFT]:
                if self._last_position:
                    cv2.line(self._canvas, self._last_position, e.restored_position, self.COLOR, self.THICKNESS)
                self._last_position = e.restored_position
            else:
                self._last_position = None

        output = self.source.value.image.copy()
        mask = (self._canvas > 0).any(-1)
        output[mask, :] = self._canvas[mask, :]
        output_frame = Frame(output, 'display')
        self.output.push(output_frame)
        self.debug.push(output_frame)
        overlay_frame = Frame(self._canvas, 'overlay')
        self.overlay.push(overlay_frame)
        self.debug.push(overlay_frame)


class Launcher(ApplicationLauncher):
    def __init__(self):
        super().__init__()
        self.add_configurator(VideoSource.configurator())
        self.add_configurator(AuxiliaryOpenCvDisplay.configurator())
        self.add_configurator(MainWindow.configurator())
        self.add_configurator(ProjectorDriver2d.configurator())

    def register_application_components(self, args, app: Application):
        source = VideoSource(VideoSource.configurator().config_from_args(args))
        aux_config = AuxiliaryOpenCvDisplay.configurator().config_from_args(args)
        aux_display = AuxiliaryOpenCvDisplay(aux_config, 'projector')
        main_window_config = MainWindow.configurator().config_from_args(args)
        driver = ProjectorDriver2d('source', 'overlay', config=ProjectorDriver2d.configurator().config_from_args(args))
        mouse_handler = EventBasedMouseHandler()
        paint_controller = PaintController()
        displays = [
            OpenCvDisplay('display'),
            OpenCvDisplay('source'),
            OpenCvDebugDisplay(),
        ]
        main_window = MainWindow(displays, config=main_window_config, auxiliary_display=aux_display,
                                 mouse_handler=mouse_handler)
        app.register(source, paint_controller, driver, main_window)


if __name__ == '__main__':
    Launcher().main()
