import time
from typing import Tuple

import pygame

from async2v.components.base import SubComponent
from async2v.components.opencv.video import Frame
from async2v.components.pygame.fonts import BEDSTEAD
from async2v.components.pygame.util.display import scale_and_center_preserving_aspect, length_normalizer, \
    best_regular_screen_layout
from async2v.components.pygame.util.opencv import opencv_to_pygame
from async2v.components.pygame.util.text import render_hud_text
from async2v.event import OPENCV_FRAME_EVENT, FPS_EVENT, DURATION_EVENT
from async2v.fields import Latest, LatestBy
from async2v.runner import Fps, Duration


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


class OpenCvMultiDisplay(Display):
    REEVALUATION_INTERVAL_SECONDS = 60
    BG_COLOR = (0, 0, 0)

    def __init__(self):
        self.__number_of_elements = 0  # type: int
        self.__surface_size = None
        self.__last_layout_evaluation = 0  # type: float
        self.__layout = None  # type: Tuple[int, int]

    @property
    def graph_colors(self) -> Tuple[str, str]:
        return '#50A0A0', '#EEFEFE'

    @property
    def frames(self) -> [Frame]:
        """
        Override this property to return a list of OpenCV frames to be rendered.
        This list should be stable during one iteration (e.g. directly calculated from the input fields).
        """
        raise NotImplementedError

    def draw(self, surface: pygame.Surface):
        surface.fill(self.BG_COLOR)
        if len(self.frames) == 0:
            return

        if (len(self.frames) != self.__number_of_elements or
                time.time() - self.__last_layout_evaluation > self.REEVALUATION_INTERVAL_SECONDS or
                surface.get_size() != self.__surface_size):
            self._calculate_layout(surface)

        target_size = surface.get_size()
        element_size = (int(target_size[0] / self.__layout[0]), int(target_size[1] / self.__layout[1]))
        for i, frame in enumerate(self.frames):
            i_x = i % self.__layout[0]
            i_y = int(i / self.__layout[0])

            frame_surface = opencv_to_pygame(frame)
            offset, target_size = scale_and_center_preserving_aspect(frame_surface.get_size(), element_size)
            target_rect = pygame.Rect(offset, target_size)
            target_rect = target_rect.move(i_x * element_size[0], i_y * element_size[1])
            target_surface = surface.subsurface(target_rect)
            pygame.transform.scale(frame_surface, target_size, target_surface)
            self.after_draw_frame(i, frame, surface, target_surface)
        self.after_draw(surface)

    def after_draw_frame(self, frame_index: int, frame: Frame, surface: pygame.Surface,
                         frame_surface: pygame.Surface) -> None:
        """
        Override to draw extra information on a single frame
        :param frame_index:
        :param frame: Frame that has been rendered
        :param surface: pygame.Surface of the whole display
        :param frame_surface: pygame.Surface the frame has been rendered to
        """

    def after_draw(self, surface: pygame.Surface) -> None:
        """
        Override to draw extra information on the whole display
        :param surface: pygame.Surface of the whole display
        """

    def _calculate_layout(self, surface: pygame.Surface):
        self.logger.debug(f'Re-calculating layout for {len(self.frames)} elements')
        frame_sizes = [(f.width, f.height) for f in self.frames]
        self.__layout = best_regular_screen_layout(frame_sizes, surface.get_size())
        self.__last_layout_evaluation = time.time()
        self.__number_of_elements = len(frame_sizes)
        self.__surface_size = surface.get_size()


class OpenCvDebugDisplay(OpenCvMultiDisplay):
    FONT_COLOR = (255, 255, 255)
    FONT_BG_COLOR = (0, 0, 0, 90)
    FONT = BEDSTEAD

    def __init__(self):
        super().__init__()
        self.input = LatestBy(OPENCV_FRAME_EVENT, lambda frame: frame.source)  # type: LatestBy[str, Frame]
        self.fps = LatestBy(FPS_EVENT, lambda fps: fps.component_id)  # type: LatestBy[str, Fps]
        self.duration = LatestBy(DURATION_EVENT, lambda d: d.component_id)  # type: LatestBy[str, Duration]

    @property
    def frames(self) -> [Frame]:
        return [v for k, v in sorted(self.input.value_dict.items(), key=lambda item: item[0])]

    def after_draw_frame(self, frame_index: int, frame: Frame, surface: pygame.Surface,
                         frame_surface: pygame.Surface) -> None:
        s = length_normalizer(surface.get_size())
        font_size = s(20)
        render_hud_text(self.FONT, frame_surface, frame.source, font_size,
                        fgcolor=self.FONT_COLOR, bgcolor=self.FONT_BG_COLOR, position=(0, 1))

    def after_draw(self, surface: pygame.Surface):
        if not self.fps.value_dict:
            return
        s = length_normalizer(surface.get_size())
        font_size = s(20)
        combined_keys = sorted(set(list(self.fps.value_dict) + list(self.duration.value_dict)))
        id_length = max([len(key) for key in combined_keys])

        # TODO there might be optimization potential: the fps dict is not updated all the time
        text = ''
        for i_y, key in enumerate(combined_keys):
            fps = self.fps.value_dict.get(key, None)
            duration = self.duration.value_dict.get(key, None)
            text += f'{key:{id_length}s}: '
            text += f'{duration.duration_seconds:4.03f}s' if duration else ' ' * 7
            text += ' | '
            text += f'{fps.current:5.01f}/{fps.target:3d}fps' if fps else ' ' * 12
            text += '\n'

        render_hud_text(self.FONT, surface, text, font_size,
                        fgcolor=self.FONT_COLOR, bgcolor=self.FONT_BG_COLOR, position=(1, 0))
