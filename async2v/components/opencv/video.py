import argparse
import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Tuple, List, Union

import sys

from async2v import event
from async2v.cli import Configurator, Command
from async2v.components.base import IteratingComponent, EventDrivenComponent
from async2v.fields import Output, Latest
from async2v.util import parse_resolution

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


@dataclass(frozen=True)
class Frame:
    """
    Container for a OpenCV video frame

    Next to the image, this class includes some convenience methods and the name of the video source.
    """

    image: numpy.ndarray
    """
    :type: numpy.ndarray

    OpenCV image
    """

    source: str
    """
    :type: str

    Name of the source. For frames emitted by builtin components, this is the `component id <Component.id>`.
    """

    @property
    def width(self) -> int:
        """
        Width of `image`
        """
        return self.image.shape[1]

    @property
    def height(self) -> int:
        """
        Height of `image`
        """
        return self.image.shape[0]

    @property
    def channels(self) -> int:
        """
        Number of channels of `image`
        """
        try:
            return self.image.shape[2]
        except IndexError:
            return 1


@dataclass
class VideoSourceConfig:
    """
    Configuration for the `VideoSource` component
    """

    path: Union[str, int]
    """
    :type: Union[str, int]

    Path to video file (`str`) or camera index (`int`)
    """

    fps: int
    """
    :type: int

    Frames per second
    """

    resolution: Tuple[int, int] = None
    """
    :type: Tuple[int, int]

    Resolution (width, height)
    """


class VideoSourceConfigurator(Configurator):
    """
    Configurator for the `VideoSource` component
    """

    def add_app_arguments(self, parser: argparse.ArgumentParser) -> None:
        group = parser.add_argument_group('Video Source',
                                          'Defaults to camera 0. If a video file is specified, the application '
                                          'terminates on end of file.')
        source_group = group.add_mutually_exclusive_group()
        source_group.add_argument('--source-camera', metavar='CAM', type=int, help='Camera index')
        source_group.add_argument('--source-file', metavar='PATH', type=str, help='Video file')
        group.add_argument('--source-fps', metavar='FPS', type=int,
                           help='Fps of video source, autodetected if not specified')
        group.add_argument('--source-resolution', metavar='WIDTHxHEIGHT')

    @property
    def commands(self) -> List[Command]:
        return []

    @staticmethod
    def config_from_args(args) -> VideoSourceConfig:
        """
        Get configuration from argparse output
        """
        if args.source_camera is not None:
            path = args.source_camera
        elif args.source_file is not None:
            path = args.source_file
        else:
            path = 0

        if args.source_fps:
            fps = args.source_fps
        else:
            print(f'Autodetecting fps from source {path}')
            temp_cap = cv2.VideoCapture(path)
            fps = temp_cap.get(cv2.CAP_PROP_FPS)
            temp_cap.release()
            print(f'Detected fps: {fps}')
            if not fps:
                print('Could not detect fps. Please specify manually with --source-fps <fps>.')
                sys.exit(1)
        if args.source_resolution:
            resolution = parse_resolution(args.source_resolution)
        else:
            resolution = None
        return VideoSourceConfig(path, int(fps), resolution)


class VideoSource(IteratingComponent):
    """
    OpenCV video source component

    Reads from a video file or a camera at a given framerate.
    The frames are pushed to the provided event key wrapped in `Frame` objects.
    Supports full command line configuration via `VideoSourceConfigurator`.
    """

    @staticmethod
    def configurator() -> VideoSourceConfigurator:
        """
        Convenience method to create a matching configurator
        """
        return VideoSourceConfigurator()

    def __init__(self, config: VideoSourceConfig, key: str = 'source'):
        """
        :param config: Can be generated via `VideoSourceConfigurator`
        :param key: Event key of video output
        """
        self._path = config.path
        self._target_fps = config.fps
        self.output = Output(key)
        self.debug_output = Output(event.OPENCV_FRAME_EVENT)
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._resolution = config.resolution
        self._resolution_verified = False
        self._capture: cv2.VideoCapture = None

    @property
    def target_fps(self) -> int:
        return self._target_fps

    @property
    def graph_colors(self) -> Tuple[str, str]:
        return '#8080F0', '#FBFBFF'

    async def setup(self):
        await asyncio.get_event_loop().run_in_executor(self._executor, self._create_capture)

    def _create_capture(self):
        self._capture = cv2.VideoCapture(self._path)
        if self._resolution:
            self._capture.set(cv2.CAP_PROP_FRAME_WIDTH, self._resolution[0])
            self._capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self._resolution[1])

    async def process(self):
        ret, image = await asyncio.get_event_loop().run_in_executor(self._executor, self._capture.read)
        if ret:
            frame = Frame(image, self.id)
            if not self._resolution_verified:
                self._verify_resolution(frame)
            self.output.push(frame)
            self.debug_output.push(frame)
        else:
            self.logger.info('Could not read frame, assuming end of file')
            self.shutdown()

    def _verify_resolution(self, frame: Frame):
        if self._resolution:
            w, h = self._resolution
            if frame.width != w or frame.height != h:
                raise ValueError(f'Expected resolution {w}x{h}, got {frame.width}x{frame.height}')
        self._resolution_verified = True
        self.logger.info(f'Source resolution {frame.width}x{frame.height}')

    async def cleanup(self):
        await asyncio.get_event_loop().run_in_executor(self._executor, self._release_capture)

    def _release_capture(self):
        self._capture.release()


class SimpleDisplaySink(EventDrivenComponent):
    """
    Simple OpenCV-based display

    Uses ``cv2.imshow`` to display frames. When the display has focus, pressing ``ESCAPE`` triggers shutdown of the
    application.
    """
    ESCAPE = 27

    def __init__(self, input_key: str):
        """
        :param input_key: Event key of the input. Needs to provide `Frame` events to display.
        """
        self.input: Latest[Frame] = Latest(input_key, trigger=True)

    async def process(self):
        cv2.imshow(self.id, self.input.value.image)
        result = cv2.waitKey(1)
        if result == -1:
            pass
        elif result & self.ESCAPE == self.ESCAPE:
            self.shutdown()

    async def cleanup(self):
        cv2.destroyWindow(self.id)
