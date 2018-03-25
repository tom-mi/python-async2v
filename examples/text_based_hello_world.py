#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK
from typing import List

import pygame

from async2v.application import Application
from async2v.cli import ApplicationLauncher
from async2v.components.pygame.display import Display
from async2v.components.pygame.keyboard import KeyboardHandler, Action, KeyboardLayout
from async2v.components.pygame.main import MainWindow
from async2v.components.pygame.mouse import MouseRegion
from async2v.components.pygame.util.display import length_normalizer
from async2v.components.pygame.util.text import render_hud_text
from async2v.fields import Latest, Output


class TextDisplay(Display):
    TEXT_COLOR = (20, 200, 255)

    def __init__(self):
        self.state = Latest('state')
        self.name = Latest('name')

    def draw(self, surface: pygame.Surface) -> List[MouseRegion]:
        surface.fill((0, 0, 0))
        s = length_normalizer(surface.get_size())
        if self.state.value is None or self.name.value is None:
            render_hud_text(surface, 'Press enter to start', size=s(30), fgcolor=self.TEXT_COLOR, position=(0.5, 0.2))
            return []
        if self.state.value == 'input':
            render_hud_text(surface, 'Enter your name:', size=s(30), fgcolor=self.TEXT_COLOR, position=(0.5, 0.2))
            render_hud_text(surface, self.name.value, size=s(50), fgcolor=self.TEXT_COLOR, position=(0.5, 0.5))
        else:
            render_hud_text(surface, 'Hello ' + self.name.value, size=s(50), fgcolor=self.TEXT_COLOR,
                            position=(0.5, 0.5))
        return []


class MyKeyboardHandler(KeyboardHandler):
    ACTIONS = [
        Action('enter', ['RETURN']),
    ]

    def __init__(self, layout: KeyboardLayout):
        super().__init__(layout)
        self.state = Output('state')
        self.name = Output('name')
        self._name = 'World'

    def key_down(self, action: str) -> None:
        self.state.push('input')
        self.capture_text('name', self._name)

    def key_up(self, action: str) -> None:
        pass

    def process(self) -> None:
        pass

    def text_capture_completed(self, capture_id: str, text: str):
        self._name = text
        self.name.push(self._name)
        self.state.push('hello')

    def text_capture_update(self, capture_id: str, text: str):
        self.name.push(text)


class Launcher(ApplicationLauncher):
    def __init__(self):
        super().__init__()
        self.add_configurator(MyKeyboardHandler.configurator())
        self.add_configurator(MainWindow.configurator())

    def register_application_components(self, args, app: Application):
        display = TextDisplay()
        main_window_config = MainWindow.configurator().config_from_args(args)
        layout = MyKeyboardHandler.configurator().layout_from_args(args)
        keyboard = MyKeyboardHandler(layout)
        main = MainWindow([display], keyboard, config=main_window_config)
        app.register(main)


if __name__ == '__main__':
    Launcher().main()
