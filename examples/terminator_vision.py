#!/usr/bin/env python3
import argparse

import asyncio
import cv2
import numpy as np

from async2v.application import Application
from async2v.cli import ApplicationLauncher
from async2v.components.base import EventDrivenComponent
from async2v.components.opencv.video import VideoSource, Frame
from async2v.components.pygame.display import OpenCvDisplay
from async2v.components.pygame.main import MainWindow
from async2v.fields import Latest, Output


class Launcher(ApplicationLauncher):

    def setup_application_arguments(self, parser: argparse.ArgumentParser):
        MainWindow.add_arguments(parser)

    def register_application_components(self, args, app: Application):
        source = VideoSource()
        display = OpenCvDisplay('terminator')
        face_detector = FaceDetector()
        terminator_filter = TerminatorFilter()
        main_window_config = MainWindow.config_from_args(args)
        main_window = MainWindow(main_window_config, displays=[display])
        app.register(source, face_detector, terminator_filter, main_window)


class TerminatorFilter(EventDrivenComponent):
    TERMINATOR_MAT = np.array(
        [[2. * 0.114, 2. * 0.587, 2. * 0.299, -200.],
         [2. * 0.114, 2. * 0.587, 2. * 0.299, -200.],
         [2. * 0.114, 2. * 0.587, 2. * 0.299, 0.]])

    def __init__(self):
        self.source = Latest('source', trigger=True)  # type: Latest[Frame]
        self.faces = Latest('faces')
        self.output = Output('terminator')  # type: Output[Frame]

    async def process(self):
        if not self.source.value:
            return
        image = self.source.value.image.copy()
        edges = cv2.Canny(image, 100, 200)
        image[edges > 0] = np.array([200, 200, 200])
        red_image = cv2.transform(image, self.TERMINATOR_MAT)
        if self.faces.value is not None:
            for (x, y, w, h) in self.faces.value:
                cv2.rectangle(red_image, (x, y), (x + w, y + h), (255, 255, 255), 2)
        self.output.push(Frame(red_image, 'terminator'))


class FaceDetector(EventDrivenComponent):
    FACE_CASCADE = '/usr/share/opencv/haarcascades/haarcascade_frontalface_default.xml'

    def __init__(self):
        self.source = Latest('source', trigger=True)  # type: Latest[Frame]
        self.face_cascade = cv2.CascadeClassifier(self.FACE_CASCADE)
        self.output = Output('faces')

    async def process(self):
        if not self.source.value:
            return
        faces = await asyncio.get_event_loop().run_in_executor(None, self._detect_faces, self.source.value.image)
        self.output.push(faces)

    def _detect_faces(self, image):
        return self.face_cascade.detectMultiScale(image, 1.3, 5)


def main():
    launcher = Launcher()
    launcher()


if __name__ == '__main__':
    main()
