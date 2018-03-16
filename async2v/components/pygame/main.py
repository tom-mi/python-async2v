import argparse
from typing import List

import pygame.display
import sys

from async2v.components.base import IteratingComponent, ContainerMixin
from async2v.components.opencv.video import Frame
from async2v.components.pygame.display import Display
from async2v.components.pygame.util import configure_display, DisplayConfiguration, list_resolutions, parse_resolution, \
    DEFAULT_CONFIG, DEFAULT_FULLSCREEN_CONFIG
from async2v.fields import LatestBy


class MainWindow(IteratingComponent, ContainerMixin):

    @staticmethod
    def add_arguments(parser: argparse.ArgumentParser):
        group = parser.add_argument_group('Display')
        group.add_argument('--fullscreen', action='store_true', help='Run display in fullscreen')
        group.add_argument('--resizable', action='store_true', help='Run display in a resizable window')
        group.add_argument('--resolution', metavar='WIDTHxHEIGHT', help='Set display resolution')
        group.add_argument('--list-resolutions', action='store_true', help='List supported resolutions')

    @staticmethod
    def config_from_args(args) -> DisplayConfiguration:
        if args.list_resolutions:
            list_resolutions()
            sys.exit()
        else:
            if args.resolution:
                resolution = parse_resolution(args.resolution)
            else:
                resolution = None
        return DisplayConfiguration(resolution, args.fullscreen, args.resizable)

    def __init__(self, config: DisplayConfiguration = None, fps: int = 60, displays: [Display] = None):
        super().__init__(displays or [])
        self._fps = fps  # type: int
        self.debug_input = LatestBy('async2v.opencv.frame',
                                    lambda event: event.value.source)  # type: LatestBy[str, Frame]
        self._config = config
        self._currently_fullscreen = config.fullscreen  # type: bool

        self._displays = list(displays or [])  # type: List[Display]
        self._surface = None  # type: pygame.Surface

    @property
    def target_fps(self) -> int:
        return self._fps

    async def setup(self):
        pygame.display.init()
        self._surface = configure_display(self._config)

    async def process(self):
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.shutdown()
                if event.key == pygame.K_F11:
                    self.toggle_fullscreen()
            elif event.type in (pygame.VIDEORESIZE, pygame.VIDEOEXPOSE):
                # TODO clean this up, maybe remove resizable altogether
                self.logger.info('Video resized')
                resolution = event.dict['size']
                self._surface = configure_display(DisplayConfiguration(resolution, resizable=True, fullscreen=False))
                self._currently_fullscreen = False

        # TODO add event handler

        for display in self._displays:
            # TODO add display switching
            display.draw(self._surface)

        pygame.display.flip()

    def toggle_fullscreen(self):
        if self._config.fullscreen and self._currently_fullscreen:
            self._surface = configure_display(DEFAULT_CONFIG)
        elif not self._config.fullscreen and not self._currently_fullscreen:
            self._surface = configure_display(DEFAULT_FULLSCREEN_CONFIG)
        else:
            self._surface = configure_display(self._config)
        self._currently_fullscreen = not self._currently_fullscreen

    async def cleanup(self):
        pygame.display.quit()
