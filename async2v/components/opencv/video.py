import asyncio
import typing
from concurrent.futures import ThreadPoolExecutor

from async2v.components.base import IteratingComponent, EventDrivenComponent
from async2v.fields import Output, Latest

try:
    import cv2
except ImportError as e:
    print('Optional module cv2 not present. Please install opencv.')
    raise e

try:
    import numpy as np
except ImportError as e:
    print('Optional module cv2 not present. Please install opencv.')
    raise e


class Frame(typing.NamedTuple):
    image: np.ndarray
    source: str

    @property
    def width(self) -> int:
        return self.image.shape[1]

    @property
    def height(self) -> int:
        return self.image.shape[0]

    @property
    def channels(self) -> int:
        try:
            return self.image.shape[2]
        except IndexError:
            return 1


class VideoSource(IteratingComponent):

    def __init__(self, path=0, key: str = 'source', target_fps: int = 60):
        self._path = path
        self._target_fps = target_fps
        self.output = Output(key)
        self.debug_output = Output('async2v.opencv.frame')
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._capture = None  # type: cv2.VideoCapture

    @property
    def target_fps(self) -> int:
        return self._target_fps

    async def setup(self):
        await asyncio.get_event_loop().run_in_executor(self._executor, self._create_capture)

    def _create_capture(self):
        self._capture = cv2.VideoCapture(self._path)

    async def process(self):
        ret, image = await asyncio.get_event_loop().run_in_executor(self._executor, self._capture.read)
        if ret:
            frame = Frame(image, self.id)
            self.output.push(frame)
            self.debug_output.push(frame)
        else:
            self.logger.error('Could not read frame')

    async def cleanup(self):
        await asyncio.get_event_loop().run_in_executor(self._executor, self._release_capture)

    def _release_capture(self):
        self._capture.release()


class SimpleDisplaySink(EventDrivenComponent):
    ESCAPE = 27

    def __init__(self, input_key: str):
        self.input = Latest(input_key, trigger=True)  # type: Latest[Frame]

    async def process(self):
        cv2.imshow(self.id, self.input.value.image)
        result = cv2.waitKey(1)
        if result == -1:
            pass
        elif result & self.ESCAPE == self.ESCAPE:
            self.shutdown()

    async def cleanup(self):
        cv2.destroyWindow(self.id)
