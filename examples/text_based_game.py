#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK
import argparse
import json
import os.path
from typing import List

import pygame

from async2v.application import Application
from async2v.cli import ApplicationLauncher, Configurator, Command
from async2v.components.base import EventDrivenComponent
from async2v.components.pygame.display import Display
from async2v.components.pygame.keyboard import Action, EventBasedKeyboardHandler, KeyboardEvent
from async2v.components.pygame.main import MainWindow
from async2v.components.pygame.util.display import length_normalizer
from async2v.components.pygame.util.text import render_hud_text
from async2v.fields import Latest, Buffer, Output


class TextDisplay(Display):
    TEXT_COLOR = (20, 200, 255)
    UNSELECTED_COLORS = ((100, 100, 100), (20, 20, 20))
    SELECTED_COLORS = ((200, 255, 200), (20, 40, 20))

    def __init__(self):
        self.text = Latest('text')
        self.choices = Latest('choices')

    def draw(self, surface: pygame.Surface):
        s = length_normalizer(surface.get_size())
        if self.text.value is None or self.choices.value is None:
            return
        surface.fill((0, 0, 0))
        render_hud_text(surface, self.text.value, size=s(18), fgcolor=self.TEXT_COLOR, position=(0.5, 0.2))
        for i, choice in enumerate(self.choices.value):
            color, bgcolor = self.SELECTED_COLORS if choice['selected'] else self.UNSELECTED_COLORS
            render_hud_text(surface, choice['text'], size=s(20), fgcolor=color, bgcolor=bgcolor,
                            position=(0.5, 0.4 + i * 0.07))


class MyKeyboardHandler(EventBasedKeyboardHandler):
    ACTIONS = [
        Action('up', ['UP']),
        Action('down', ['DOWN']),
        Action('choose', ['RETURN']),
    ]


class GameConfigurator(Configurator):

    def add_app_arguments(self, parser: argparse.ArgumentParser) -> None:
        default_game = os.path.join(os.path.dirname(__file__), 'game.json')
        parser.add_argument('--game', help='Json file containing the game', default=default_game)

    @property
    def commands(self) -> List[Command]:
        return []

    @staticmethod
    def load_game(args):
        with open(args.game) as f:
            return json.loads(f.read())


class GameController(EventDrivenComponent):
    def __init__(self, game):
        self.game = game
        self.node = 'start'
        self.selection = 0

        self.keyboard = Buffer(EventBasedKeyboardHandler.KEYBOARD_EVENT, trigger=True)  # type: Buffer[KeyboardEvent]

        self.text = Output('text')
        self.choices = Output('choices')

    async def setup(self):
        self._publish_state()

    async def process(self):
        changed = False
        choices = self.game[self.node]['choices']
        for event in self.keyboard.values:
            if event.active:
                if event.action == 'up' and self.selection > 0:
                    self.selection -= 1
                    changed = True
                elif event.action == 'down' and self.selection + 1 < len(choices):
                    self.selection += 1
                    changed = True
                elif event.action == 'choose' and len(choices):
                    choice = choices[self.selection]
                    self.node = choice['goto']
                    self.selection = 0
                    changed = True

        if changed:
            self._publish_state()

    def _publish_state(self):
        node = self.game[self.node]
        self.text.push(node['text'])
        choices = [{'text': choice['text'], 'selected': i == self.selection}
                   for i, choice in enumerate(node['choices'])]
        self.choices.push(choices)


class Launcher(ApplicationLauncher):
    def __init__(self):
        super().__init__()
        self.add_configurator(MyKeyboardHandler.configurator())
        self.add_configurator(MainWindow.configurator())
        self.add_configurator(GameConfigurator())

    def register_application_components(self, args, app: Application):
        display = TextDisplay()
        main_window_config = MainWindow.configurator().config_from_args(args)
        layout = MyKeyboardHandler.configurator().layout_from_args(args)
        keyboard = MyKeyboardHandler(layout)
        main = MainWindow([display], keyboard, config=main_window_config)
        game = GameConfigurator.load_game(args)
        game_controller = GameController(game)
        app.register(game_controller, main)


if __name__ == '__main__':
    Launcher().main()
