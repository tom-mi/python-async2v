"""
Pygame main window

To use any of the pygame components & utilities, a pygame `MainWindow` component needs to be part of the application.
It is the central container for displays, keyboard & mouse handling.

It comes with a configurator to set the desired resolution and initial fullscreen mode via command line.

Example for integrating the main window into the application:

::

    class Launcher(ApplicationLauncher):

        def __init__(self):
            super().__init__()
            self.add_configurator(MyKeyboardHandler.configurator())
            self.add_configurator(MainWindow.configurator())

        def register_application_components(self, args, app: Application):
            displays = [
                # add displays here
                OpenCvDebugDisplay(),
            ]
            main_window_config = MainWindow.configurator().config_from_args(args)
            main = MainWindow(displays, config=main_window_config)
            # add more components here
            app.register(main)
"""
import argparse
from dataclasses import dataclass
from datetime import datetime
from typing import List, Tuple, Optional

import pygame.display

from async2v.application import Application
from async2v.cli import Configurator, Command
from async2v.components.base import IteratingComponent, ContainerMixin
from async2v.components.pygame.display import Display, AuxiliaryDisplay
from async2v.components.pygame.gui import render_hud_text
from async2v.components.pygame.keyboard import KeyboardHandler, _NoOpKeyboardHandler
from async2v.components.pygame.mouse import MouseRegion, ROOT_REGION, MouseHandler, _NoOpMouseHandler
from async2v.error import ConfigurationError
from async2v.util import parse_resolution, length_normalizer


@dataclass
class DisplayConfiguration:
    """
    Display configuration for `MainWindow`
    """
    resolution: Optional[Tuple[int, int]]
    fullscreen: bool

    def __str__(self):
        if self.fullscreen:
            mode = 'fullscreen'
        else:
            mode = 'window'
        return f'{self.resolution[0]}x{self.resolution[1]} {mode}'


_DEFAULT_CONFIG = DisplayConfiguration((800, 600), False)
_DEFAULT_FULLSCREEN_CONFIG = DisplayConfiguration(None, True)


class MainWindowConfigurator(Configurator):
    """
    Configurator for `MainWindow`
    """

    class ListResolutionCommand(Command):
        name = 'list-resolutions'
        help = 'List supported fullscreen resolutions'
        needs_app = False

        def add_arguments(self, parser: argparse.ArgumentParser):
            pass

        def __call__(self, args, app: Application = None):
            pygame.display.init()
            print('Available fullscreen resolutions:')
            for mode in pygame.display.list_modes():
                print(f'    {mode[0]}x{mode[1]}')

    def add_app_arguments(self, parser: argparse.ArgumentParser) -> None:
        group = parser.add_argument_group('Display')
        group.add_argument('--fullscreen', action='store_true')
        group.add_argument('--resolution', metavar='WIDTHxHEIGHT')

    @property
    def commands(self) -> List[Command]:
        return [self.ListResolutionCommand()]

    @staticmethod
    def config_from_args(args) -> DisplayConfiguration:
        """
        Get configuration from argparse output
        """
        if args.resolution:
            resolution = parse_resolution(args.resolution)
        else:
            resolution = None
        return DisplayConfiguration(resolution, args.fullscreen)


class MainWindow(IteratingComponent, ContainerMixin):
    """
    Pygame main window component

    Holds up to 9 pygame `Display` subcomponents. Optionally a `KeyboardHandler`, `MouseHandler` and an
    `AuxiliaryDisplay` can be specified.

    All display & input logic should be in those subcomponents, usually there is no need to subclass `MainWindow`.

    The `MainWindow` comes with a few predefined key bindings:
        * ``F1`` to toggle on screen help
        * ``F2`` .. ``F10`` for switching displays
        * ``F11`` to toggle fullscreen mode
        * ``F12`` to take a screenshot
        * ``ESCAPE`` to shutdown the application
    """
    HELP_FONT_COLOR = (255, 255, 255)
    HELP_BG_COLOR = (0, 0, 0, 120)

    @classmethod
    def configurator(cls) -> MainWindowConfigurator:
        """
        Convenience method to create a matching configurator
        """
        return MainWindowConfigurator()

    def __init__(self, displays: List[Display], auxiliary_display: AuxiliaryDisplay = None,
                 keyboard_handler: KeyboardHandler = None, mouse_handler: MouseHandler = None,
                 config: DisplayConfiguration = None, fps: int = 60, ):
        """
        :param displays: List of up to 9 displays
        :param auxiliary_display:
        :param keyboard_handler:
        :param mouse_handler:
        :param config: Can be generated via `MainWindowConfigurator`
        :param fps: Target frame rate (frames per second)
        """
        if keyboard_handler is None:
            keyboard_handler = _NoOpKeyboardHandler()
        if mouse_handler is None:
            mouse_handler = _NoOpMouseHandler()
        if auxiliary_display and auxiliary_display.resolution is None:
            auxiliary_display = None
        sub_components = [*displays, keyboard_handler, mouse_handler]
        if auxiliary_display:
            sub_components.append(auxiliary_display)
        super().__init__(sub_components)
        if len(displays) == 0:
            raise ConfigurationError('Need at least 1 display')
        elif len(displays) > 9:
            raise ConfigurationError('Currently, no more than 9 displays are supported')

        self._fps = fps  # type: int
        if config is None:
            self._display_config = {
                False: _DEFAULT_CONFIG,
                True: _DEFAULT_FULLSCREEN_CONFIG,
            }
        elif config.fullscreen:
            self._display_config = {
                False: _DEFAULT_CONFIG,
                True: config,
            }
        else:
            self._display_config = {
                False: config,
                True: _DEFAULT_FULLSCREEN_CONFIG,
            }
        self._currently_fullscreen: bool = config.fullscreen if config else False

        self._displays: List[Display] = list(displays)
        self._current_display: int = 0
        self._surface: pygame.Surface = None

        self._aux_display = None
        self._aux_surface = None
        if auxiliary_display:
            self._aux_display = auxiliary_display

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
        self._configure_display()
        self._configure_aux_display()
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
                elif event.key == pygame.K_F12:
                    self._take_screenshot()
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

        if self._aux_surface:
            self._aux_display.draw(self._aux_surface)

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
        self._currently_fullscreen = not self._currently_fullscreen
        self._configure_display()
        self._configure_aux_display()

    def _configure_display(self):
        config = self._display_config[self._currently_fullscreen]
        resolution = config.resolution
        if resolution is None:
            if config.fullscreen:
                resolution = pygame.display.list_modes()[0]
            else:
                resolution = _DEFAULT_CONFIG.resolution
            config = DisplayConfiguration(resolution, config.fullscreen)

        flags = self._get_best_flags_for_config(config)
        self.logger.info(f'Setting display mode to {config}')
        self._surface = pygame.display.set_mode(resolution, flags)

    def _get_best_flags_for_config(self, config: DisplayConfiguration):
        if config.fullscreen:
            base_flags = pygame.FULLSCREEN
        else:
            base_flags = 0

        hw_accelerated_flags = pygame.HWACCEL | pygame.DOUBLEBUF | base_flags

        if pygame.display.mode_ok(config.resolution, hw_accelerated_flags):
            self.logger.info('Using hardware accelerated display')
            return hw_accelerated_flags
        elif pygame.display.mode_ok(config.resolution, base_flags):
            self.logger.info('Using software display')
            return base_flags
        else:
            raise RuntimeError(f'Display mode {config} is not supported')

    def _configure_aux_display(self):
        if self._currently_fullscreen and self._aux_display:
            w, h = self._surface.get_size()
            a_w, a_h = self._aux_display.resolution
            target_main_rect = pygame.Rect(0, 0, w - a_w, h)
            target_aux_rect = pygame.Rect(w - a_w, 0, a_w, a_h)
            self._aux_surface = self._surface.subsurface(target_aux_rect)
            self._surface = self._surface.subsurface(target_main_rect)
        else:
            self._aux_surface = None

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
            ('Take screenshot', 'F12'),
        ]
        entries += self._keyboard_handler._layout.help

        desc_len = max(len(d) for d, k in entries)
        return '\n'.join(f'{d:{desc_len}s}  {k}' for d, k in entries)

    def _take_screenshot(self):
        path = f'screenshot-{datetime.now():%Y%m%d_%H%M%S}.png'
        self.logger.info(f'Saving screenshot to {path}')
        pygame.image.save(self._surface, path)

    async def cleanup(self):
        pygame.display.quit()
