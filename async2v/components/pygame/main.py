import argparse
from typing import List, Tuple

import pygame.display

from async2v.application import Application
from async2v.cli import Configurator, Command
from async2v.components.base import IteratingComponent, ContainerMixin
from async2v.components.pygame.display import Display
from async2v.components.pygame.keyboard import KeyboardHandler, NoOpKeyboardHandler
from async2v.components.pygame.mouse import MouseRegion, ROOT_REGION, MouseHandler, NoOpMouseHandler
from async2v.components.pygame.util.display import configure_display, DisplayConfiguration, list_resolutions, \
    DEFAULT_CONFIG, DEFAULT_FULLSCREEN_CONFIG, length_normalizer
from async2v.components.pygame.util.text import render_hud_text
from async2v.util import parse_resolution
from async2v.error import ConfigurationError


class MainWindowConfigurator(Configurator):
    class ListResolutionCommand(Command):
        name = 'list-resolutions'
        help = 'List supported fullscreen resolutions'
        needs_app = False

        def add_arguments(self, parser: argparse.ArgumentParser):
            pass

        def __call__(self, args, app: Application = None):
            list_resolutions()

    def add_app_arguments(self, parser: argparse.ArgumentParser) -> None:
        group = parser.add_argument_group('Display')
        group.add_argument('--fullscreen', action='store_true')
        group.add_argument('--resolution', metavar='WIDTHxHEIGHT')

    @property
    def commands(self) -> List[Command]:
        return [self.ListResolutionCommand()]

    @staticmethod
    def config_from_args(args) -> DisplayConfiguration:
        if args.resolution:
            resolution = parse_resolution(args.resolution)
        else:
            resolution = None
        return DisplayConfiguration(resolution, args.fullscreen)


class MainWindow(IteratingComponent, ContainerMixin):
    HELP_FONT_COLOR = (255, 255, 255)
    HELP_BG_COLOR = (0, 0, 0, 120)

    @classmethod
    def configurator(cls) -> MainWindowConfigurator:
        """
        Returns a MainWindowConfigurator, which should be registered via add_configurator in the application launcher.
        """
        return MainWindowConfigurator()

    def __init__(self, displays: List[Display],
                 keyboard_handler: KeyboardHandler = None, mouse_handler: MouseHandler = None,
                 config: DisplayConfiguration = None, fps: int = 60, ):
        if keyboard_handler is None:
            keyboard_handler = NoOpKeyboardHandler()
        if mouse_handler is None:
            mouse_handler = NoOpMouseHandler()
        super().__init__([*displays, keyboard_handler, mouse_handler])
        if len(displays) == 0:
            raise ConfigurationError('Need at least 1 display')
        elif len(displays) > 9:
            raise ConfigurationError('Currently, no more than 9 displays are supported')

        self._fps = fps  # type: int
        self._config = config
        self._currently_fullscreen = config.fullscreen  # type: bool

        self._displays = list(displays)  # type: List[Display]
        self._current_display = 0  # type: int
        self._surface = None  # type: pygame.Surface

        self._keyboard_handler = keyboard_handler
        self._mouse_handler = mouse_handler

        self._regions = None  # type: List[MouseRegion]

        self._help_visible = False
        self._help_text = self._generate_help_text()

    @property
    def target_fps(self) -> int:
        return self._fps

    @property
    def graph_colors(self) -> Tuple[str, str]:
        return '#50E020', '#EEFEEB'

    async def setup(self):
        pygame.display.init()
        self._surface = configure_display(self._config)
        self._regions = [self._main_region()]

    async def process(self):
        self._mouse_handler.push_regions(self._regions)
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.shutdown()
                elif event.key == pygame.K_F1:
                    self._help_visible = not self._help_visible
                elif pygame.K_F2 <= event.key <= pygame.K_F10:
                    new_display = event.key - pygame.K_F2
                    self.change_display(new_display)
                elif event.key == pygame.K_F11:
                    self.toggle_fullscreen()
                else:
                    self._keyboard_handler.push_key_down(event.key, event.scancode, event.unicode)
            elif event.type == pygame.KEYUP:
                self._keyboard_handler.push_key_up(event.key, event.scancode)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                self._mouse_handler.push_button_down(event.pos, event.button)
            elif event.type == pygame.MOUSEBUTTONUP:
                self._mouse_handler.push_button_up(event.pos, event.button)
            elif event.type == pygame.MOUSEMOTION:
                self._mouse_handler.push_movement(event.pos, event.rel, event.buttons)

        self._regions = [self._main_region()]
        self._regions += self._displays[self._current_display].draw(self._surface)

        if self._help_visible:
            s = length_normalizer(self._surface.get_size())
            render_hud_text(self._surface, self._help_text,
                            position=(0.5, 0.5),
                            size=min(s(30), self._surface.get_height() // (1.5 * len(self._help_text.splitlines()))),
                            fgcolor=self.HELP_FONT_COLOR, bgcolor=self.HELP_BG_COLOR)

        pygame.display.flip()

    def _main_region(self) -> MouseRegion:
        return MouseRegion(ROOT_REGION, self._surface.get_rect(), self._surface.get_size())

    def toggle_fullscreen(self):
        if self._config.fullscreen and self._currently_fullscreen:
            self._surface = configure_display(DEFAULT_CONFIG)
        elif not self._config.fullscreen and not self._currently_fullscreen:
            self._surface = configure_display(DEFAULT_FULLSCREEN_CONFIG)
        else:
            self._surface = configure_display(self._config)
        self._currently_fullscreen = not self._currently_fullscreen

    def change_display(self, new_display: int):
        if 0 <= new_display < len(self._displays):
            self._current_display = new_display
        else:
            self.logger.error(f'Cannot switch to invalid display {new_display}')

    def _generate_help_text(self):
        entries = [
            ('Exit', 'ESCAPE'),
            ('Toggle help', 'F1'),
        ]
        if len(self._displays) > 1:
            entries += [('Switch displays', f'F2 .. F{len(self._displays) + 1}')]
        entries += [
            ('Toggle fullscreen', 'F11'),
        ]
        entries += self._keyboard_handler._layout.help

        desc_len = max(len(d) for d, k in entries)
        return '\n'.join(f'{d:{desc_len}s}  {k}' for d, k in entries)

    async def cleanup(self):
        pygame.display.quit()
