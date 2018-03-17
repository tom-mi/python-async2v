from typing import Tuple

import pygame
import time

from async2v.components.base import SubComponent
from async2v.components.opencv.video import Frame
from async2v.components.pygame import util
from async2v.components.pygame.fonts import BEDSTEAD
from async2v.components.pygame.opencvutil import opencv_to_pygame
from async2v.components.pygame.util import scale_and_center_preserving_aspect
from async2v.event import OPENCV_FRAME_EVENT, FPS_EVENT
from async2v.fields import Latest, LatestBy
from async2v.runner import Fps


class Display(SubComponent):

    def draw(self, surface: pygame.Surface):
        raise NotImplementedError


class OpenCvDisplay(Display):

    def __init__(self, source):
        self.input = Latest(source)  # type: Latest[Frame]

    @property
    def graph_colors(self) -> Tuple[str, str]:
        return '#50A0A0', '#EEFEFE'

    def draw(self, surface: pygame.Surface):
        if not self.input.value:
            return
        frame_surface = opencv_to_pygame(self.input.value)
        offset, target_size = scale_and_center_preserving_aspect(frame_surface.get_size(), surface.get_size())
        target_rect = pygame.Rect(offset, target_size)
        target_surface = surface.subsurface(target_rect)
        pygame.transform.scale(frame_surface, target_size, target_surface)


class OpenCvDebugDisplay(Display):
    REEVALUATION_INTERVAL_SECONDS = 60
    BG_COLOR = (0, 0, 0)
    FONT_COLOR = (255, 255, 255)
    FONT = BEDSTEAD

    def __init__(self):
        self.input = LatestBy(OPENCV_FRAME_EVENT, lambda frame: frame.source)  # type: LatestBy[str, Frame]
        self.fps = LatestBy(FPS_EVENT, lambda fps: fps.component_id)  # type: LatestBy[str, Fps]
        self._number_of_elements = 0  # type: int
        self._last_layout_evaluation = 0  # type: float
        self._layout = None  # type: Tuple[int, int]

    @property
    def graph_colors(self) -> Tuple[str, str]:
        return '#50A0A0', '#EEFEFE'

    def draw(self, surface: pygame.Surface):
        surface.fill(self.BG_COLOR)
        self._draw_frames(surface)
        self._draw_fps(surface)

    def _draw_frames(self, surface: pygame.Surface):
        if len(self.input.value_dict) == 0:
            return
        if (len(self.input.value_dict) != self._number_of_elements or
                time.time() - self._last_layout_evaluation > self.REEVALUATION_INTERVAL_SECONDS):
            start = time.time()
            self._calculate_layout(surface)
            self.logger.debug(f'Re-calculating layout for {len(self.input.value_dict)} elements '
                              f'took {time.time() - start:0.6f} seconds')

        target_size = surface.get_size()
        element_size = (int(target_size[0] / self._layout[0]), int(target_size[1] / self._layout[1]))
        for i, key in enumerate(sorted(self.input.value_dict)):
            frame = self.input.value_dict[key]
            i_x = i % self._layout[0]
            i_y = int(i / self._layout[0])

            frame_surface = opencv_to_pygame(frame)
            offset, target_size = scale_and_center_preserving_aspect(frame_surface.get_size(), element_size)
            target_rect = pygame.Rect(offset, target_size)
            target_rect = target_rect.move(i_x * element_size[0], i_y * element_size[1])
            target_surface = surface.subsurface(target_rect)
            pygame.transform.scale(frame_surface, target_size, target_surface)

    def _draw_fps(self, surface: pygame.Surface):
        if not self.fps.value_dict:
            return
        s = util.normalizer(surface.get_size())
        id_length = max([len(key) for key in self.fps.value_dict])

        # TODO there might be optimization potential: the fps dict is not updated all the time
        for i_y, key in enumerate(sorted(self.fps.value_dict)):
            fps = self.fps.value_dict[key]
            text = f'{key:{id_length}s}: {fps.current:6.02f} / {fps.target} fps'
            text_surface, _ = self.FONT.render(text, self.FONT_COLOR, size=s(20))
            text_rect = text_surface.get_rect()
            target_rect = text_rect.move(surface.get_width() - text_rect.w, i_y * text_rect.h)
            surface.blit(text_surface, target_rect)

    def _calculate_layout(self, surface: pygame.Surface):
        frame_sizes = [(f.width, f.height) for f in self.input.value_dict.values()]
        self._layout = util.best_regular_screen_layout(frame_sizes, surface.get_size())
        self._last_layout_evaluation = time.time()
        self._number_of_elements = len(frame_sizes)
