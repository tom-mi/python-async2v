import argparse
import time
from dataclasses import dataclass
from typing import List

try:
    import cv2
except ImportError as e:
    print('Optional module cv2 not present. Please install opencv.')
    raise e

try:
    import numpy
except ImportError as e:
    print('Optional module numpy not present. Please install numpy.')
    raise e

from async2v import event
from async2v.cli import Configurator, Command
from async2v.components.base import EventDrivenComponent, SubComponent, ContainerMixin
from async2v.components.opencv.video import Frame
from async2v.fields import Output, Latest


@dataclass
class ProjectorDriver2dConfiguration:
    """
    Configuration for the `ProjectorDriver2d` component
    """

    debug: bool = False
    """
    :type: bool

    Emit debug frames during projector calibration
    """


class ProjectorDriver2dConfigurator(Configurator):
    """
    Configurator for the `ProjectorDriver2d` component
    """

    def add_app_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument('--debug-projector-calibration', action='store_true',
                            help='Emit debug frames during projector calibration')

    @property
    def commands(self) -> List[Command]:
        return []

    @staticmethod
    def config_from_args(args):
        """
        Get configuration from argparse output
        """
        return ProjectorDriver2dConfiguration(args.debug_projector_calibration)


class ProjectorDriver2d(EventDrivenComponent, ContainerMixin):
    """
    Draw overlays into the real world with a projector

    This component automatically calibrates a projector that projects into the field of view of a camera.
    Overlays can then be drawn in coordinates of the camera image. Calibration is performed automatically on start.
    It can also be triggered later by sending an arbitrary event to the key stored in `RESET_CALIBRATION_TRIGGER`.
    """

    #: Event key for reset command input. Events on this key trigger a new projector calibration.
    RESET_CALIBRATION_TRIGGER = 'async2v.projector.trigger.reset_calibration'

    @staticmethod
    def configurator() -> ProjectorDriver2dConfigurator:
        """
        Convenience method to create a matching configurator
        """
        return ProjectorDriver2dConfigurator()

    def __init__(self, source: str, overlay: str, projector: str = 'projector',
                 config: ProjectorDriver2dConfiguration = ProjectorDriver2dConfiguration()):
        """
        :param source: Key of the video stream input. Needs to provide events with `Frame` payload.
        :param overlay: Key of the overlay input. Needs to provide events with `Frame` payload.
        :param projector: Key of projector output. `Frame` events are pushed to this output.
        :param config: Can be generated via `ProjectorDriver2dConfigurator`
        """
        self._calibrator = _ProjectorCalibrator2d(source, projector, config.debug)
        super().__init__([self._calibrator])
        self.overlay: Latest[Frame] = Latest(overlay, trigger=True)
        self.projector = Output(projector)
        self.reset = Latest(self.RESET_CALIBRATION_TRIGGER, trigger=True)
        self._calibration_started = False

    async def process(self):
        if self.reset.updated:
            self._calibrator.reset()

        if self._calibrator.needs_calibration():
            if not self._calibration_started:
                self._calibration_started = True
                self.logger.info('Starting projector calibration')
            self._calibrator.calibrate()
        elif self._calibration_started:
            self.logger.info('Finished projector calibration')
            self._calibration_started = False
            self._draw_overlay()
        elif self.overlay.updated:
            self._draw_overlay()

    def _draw_overlay(self):
        if not self.overlay.value:
            return

        canvas = cv2.warpPerspective(self.overlay.value.image,
                                     self._calibrator.transformation_matrix,
                                     self._calibrator.CANVAS_SIZE)
        canvas_frame = Frame(canvas, 'projector')
        self.projector.push(canvas_frame)


class _ProjectorCalibrator2d(SubComponent):
    KERNEL = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))

    CANVAS_SIZE = (1200, 900)  # TODO make this configurable in a sane way
    CALIBRATION_LEARNING_DURATION = 10
    CALIBRATION_PATTERN_GRID_SIZE = 100
    CALIBRATION_CYCLE = [
        ('learn_background', CALIBRATION_LEARNING_DURATION),
        ('draw_pattern', 1),
        ('wait', 5),
        ('calibrate_pattern', 5),
        ('clear_pattern', 1),
        ('wait', 5),
    ]

    def __init__(self, source, projector, debug):
        self._background: cv2.BackgroundSubtractor = cv2.createBackgroundSubtractorMOG2()
        self._calibration_cycle_i = 0
        self._initialize_pattern()
        self.source: Latest[Frame] = Latest(source, trigger=True)
        self.projector = Output(projector)
        if debug:
            self.debug = Output(event.OPENCV_FRAME_EVENT)
        else:
            self.debug = None
        self._last_calibrated = 0
        self._transformation_matrix = None

    def reset(self) -> None:
        self._transformation_matrix = None

    def needs_calibration(self) -> bool:
        return self._transformation_matrix is None

    @property
    def transformation_matrix(self):
        return self._transformation_matrix

    def calibrate(self):
        if self.source.value is None:
            return
        self._calibration_cycle_i = (self._calibration_cycle_i + 1) % sum([n for action, n in self.CALIBRATION_CYCLE])
        action = self._calibration_action()
        if action == 'learn_background':
            self._background.apply(self.source.value.image, learningRate=1 / self.CALIBRATION_LEARNING_DURATION)
        elif action == 'wait':
            pass
        elif action == 'draw_pattern':
            pattern = self._draw_pattern()
            self._push_pattern_to_projector(pattern)
        elif action == 'clear_pattern':
            pattern = numpy.zeros(tuple(reversed(self.CANVAS_SIZE)), dtype=numpy.uint8)
            cv2.rectangle(pattern, (0, 0), self.CANVAS_SIZE, 128, self.CALIBRATION_PATTERN_GRID_SIZE)
            self._push_pattern_to_projector(pattern)
        elif action == 'calibrate_pattern':
            mask = self._background.apply(self.source.value.image, learningRate=0)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, self.KERNEL)
            mask = cv2.blur(mask, (5, 5))
            blob_detector = self._create_blob_detector()
            found, centers = cv2.findCirclesGrid(mask, self._calibration_pattern_size,
                                                 cv2.CALIB_CB_ASYMMETRIC_GRID + cv2.CALIB_CB_CLUSTERING,
                                                 blob_detector, None)
            if self.debug:
                output = self.source.value.image.copy()
                blobs = blob_detector.detect(mask)
                output = cv2.drawKeypoints(output, blobs, numpy.array([]), (0, 0, 255),
                                           cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS)
                cv2.drawChessboardCorners(output, self._calibration_pattern_size, centers, found)
                self.debug.push(Frame(mask, 'projector.calibration.mask'))
                self.debug.push(Frame(output, 'projector.calibration.debug'))
            if found:
                self._finish_calibration(centers)
        else:
            raise ValueError(f'Unknown action {action}')

    def _draw_pattern(self):
        overlay = numpy.zeros(tuple(reversed(self.CANVAS_SIZE)), dtype=numpy.uint8)
        cv2.rectangle(overlay, (0, 0), self.CANVAS_SIZE, 128, self.CALIBRATION_PATTERN_GRID_SIZE)
        r = int(self.CALIBRATION_PATTERN_GRID_SIZE * 0.2)
        for pos in self._calibration_pattern:
            cv2.circle(overlay, pos, r, (255, 255, 255), -1)
        return overlay

    def _initialize_pattern(self):
        x0 = int(self.CANVAS_SIZE[0] * 0.25)
        y0 = int(self.CANVAS_SIZE[1] * 0.25)
        a0 = self.CALIBRATION_PATTERN_GRID_SIZE
        a1 = numpy.sqrt(3) / 2 * a0
        n_x = int(self.CANVAS_SIZE[0] * 0.25 / a0) * 2 + 1
        n_y = int(self.CANVAS_SIZE[1] * 0.25 / a1) * 2 + 1

        circles = []
        for j in range(n_y):
            for i in range(n_x):
                x = int(x0 + i * a0 + (j % 2) * 0.5 * a0)
                y = int(y0 + j * a1)
                circles.append((x, y))

        self._calibration_pattern = circles
        self._calibration_pattern_size = (n_x, n_y)

    def _calibration_action(self):
        n = 0
        for action, duration in self.CALIBRATION_CYCLE:
            if n <= self._calibration_cycle_i < n + duration:
                return action
            n += duration
        else:
            raise RuntimeError(f'Invalid calibration state {self._calibration_cycle_i}')

    def _create_blob_detector(self):
        input_size = min(self.source.value.width, self.source.value.height)
        min_distance = int(input_size / 40)
        params = cv2.SimpleBlobDetector_Params()
        params.blobColor = 255
        params.filterByConvexity = False
        params.filterByArea = True
        params.filterByCircularity = True
        params.filterByColor = True
        params.filterByInertia = False
        params.minDistBetweenBlobs = min_distance
        params.minCircularity = 0.7
        params.minArea = int((min_distance * 0.1) ** 2)
        return cv2.SimpleBlobDetector_create(params)

    def _finish_calibration(self, detected_centers):
        canvas_centers = numpy.array(self._calibration_pattern, dtype='float32')
        self._transformation_matrix, _ = cv2.findHomography(detected_centers, canvas_centers)
        self._last_calibrated = time.time()
        self._calibration_cycle_i = 0

    def _push_pattern_to_projector(self, pattern):
        frame = Frame(pattern, 'projector')
        self.projector.push(frame)
        if self.debug:
            self.debug.push(frame)
