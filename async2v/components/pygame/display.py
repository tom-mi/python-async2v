from typing import Tuple

from async2v.components.base import SubComponent
from async2v.components.opencv.video import Frame
from async2v.components.pygame.opencvutil import opencv_to_pygame
from async2v.components.pygame.util import scale_and_center_preserving_aspect
from async2v.fields import Latest

import pygame


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
        scaled = pygame.transform.scale(frame_surface, target_size)
        target_rect = scaled.get_rect().move(offset)
        surface.blit(scaled, target_rect)
