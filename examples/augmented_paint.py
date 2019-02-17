#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK
from typing import List

import cv2
import numpy as np
import pygame

from async2v import event
from async2v.application import Application
from async2v.cli import ApplicationLauncher
from async2v.components.base import EventDrivenComponent
from async2v.components.opencv.projector import ProjectorDriver2d
from async2v.components.opencv.video import VideoSource, Frame
from async2v.components.pygame.display import OpenCvDebugDisplay, AuxiliaryOpenCvDisplay, OpenCvDisplay
from async2v.components.pygame.gui import Menu, Button, Label
from async2v.components.pygame.main import MainWindow
from async2v.components.pygame.mouse import EventBasedMouseHandler, MouseMovement, MouseEvent, MouseButton, MouseRegion
from async2v.fields import Latest, Output, Buffer


class PaintController(EventDrivenComponent):
    COLOR = (0, 255, 0)
    BG_COLOR = (0, 0, 0)
    THICKNESS = 4

    def __init__(self):
        self.source = Latest('source', trigger=True)  # type: Latest[Frame]
        self.output = Output('display')
        self.overlay = Output('overlay')
        self.mouse_movement = Buffer(EventBasedMouseHandler.MOUSE_MOVEMENT, trigger=True)  # type: Buffer[MouseMovement]
        self.clear_canvas = Latest('trigger.clear_canvas', trigger=True)
        self.debug = Output(event.OPENCV_FRAME_EVENT)
        self._canvas = None
        self._last_position = None

    async def process(self):
        if not self.source.value:
            return

        if self.clear_canvas.updated:
                self._canvas = None

        if self._canvas is None:
            self._canvas = np.zeros(self.source.value.image.shape, dtype='uint8')

        for e in self.mouse_movement.values:
            if e.region.name in ['display', 'VideoSource0'] and e.buttons[MouseButton.LEFT]:
                if self._last_position:
                    cv2.line(self._canvas, self._last_position, e.restored_position, self.COLOR, self.THICKNESS)
                self._last_position = e.restored_position
            elif e.region.name in ['display', 'VideoSource0'] and e.buttons[MouseButton.RIGHT]:
                if self._last_position:
                    cv2.line(self._canvas, self._last_position, e.restored_position, self.BG_COLOR, self.THICKNESS)
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


class PaintDisplay(OpenCvDisplay):

    def __init__(self, source):
        super().__init__(source)
        self.mouse_event: Buffer[MouseEvent] = Buffer(EventBasedMouseHandler.MOUSE_EVENT)
        self.reset_calibration = Output(ProjectorDriver2d.RESET_CALIBRATION_TRIGGER)
        self.clear_canvas = Output('trigger.clear_canvas')

        self._menu = Menu([
            Label('Menu'),
            Button('Calibrate', self.calibrate),
            Button('Clear Canvas', self.clear),
        ], position=(1, 0))

    def calibrate(self):
        self.reset_calibration.push(None)

    def clear(self):
        self.clear_canvas.push(None)

    def draw(self, surface: pygame.Surface) -> List[MouseRegion]:
        regions = super().draw(surface)
        self._menu.handle_mouse_events(self.mouse_event.values)
        regions += self._menu.draw(surface)
        return regions


class Launcher(ApplicationLauncher):
    def __init__(self):
        super().__init__()
        self.add_configurator(MainWindow.configurator())

    def register_application_components(self, args, app: Application):
        main_window_config = MainWindow.configurator().config_from_args(args)
        mouse_handler = EventBasedMouseHandler()
        displays = [
            OpenCvDebugDisplay(),
        ]
        main_window = MainWindow(displays, config=main_window_config, mouse_handler=mouse_handler)
        app.register(main_window)


if __name__ == '__main__':
    Launcher().main()
