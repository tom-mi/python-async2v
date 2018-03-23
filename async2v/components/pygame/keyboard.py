import argparse
import collections
import os.path
from typing import List, NamedTuple, Dict, Tuple

import logwood
import pygame

from async2v.application import Application
from async2v.cli import Configurator, Command
from async2v.components.base import SubComponent
from async2v.error import ConfigurationError
from async2v.fields import Output, Latest


class Action:

    def __init__(self, name: str, defaults: List[str] = None, description: str = None):
        if len(name.split()) != 1 or name.strip() != name:
            raise ConfigurationError(f'Invalid action name {name}, use a non-empty string without whitespace')
        self._name = name
        self._defaults = defaults or []
        self._description = description

    @property
    def name(self) -> str:
        return self._name

    @property
    def defaults(self) -> List[str]:
        return self._defaults

    @property
    def description(self) -> str:
        return self._description


class KeyboardLayout(NamedTuple):
    actions_by_key: Dict[int, str]
    actions_by_scancode: Dict[int, str]

    def action_by_key_or_scancode(self, key: int, scancode: int) -> str:
        result = self.actions_by_key.get(key, None)
        if result:
            return result
        return self.actions_by_scancode.get(scancode, None)


class KeyboardConfigurator(Configurator):

    def __init__(self, actions: List[Action]):
        self._actions = actions
        self._validate_actions()

    def add_app_arguments(self, parser: argparse.ArgumentParser) -> None:
        group = parser.add_argument_group('Keyboard')
        group.add_argument('-l', '--keyboard-layout', metavar='FILE', default='keyboard.conf',
                           help='Keyboard layout file, defaults to keyboard.conf')

    @property
    def commands(self) -> List[Command]:
        return [self.CreateDefaultLayoutCommand(self)]

    class CreateDefaultLayoutCommand(Command):
        name = 'create-keyboard-layout'
        help = 'Create a keyboard layout file containing the default layout'
        needs_app = False

        def __init__(self, configurator: 'KeyboardConfigurator'):
            self._configurator = configurator

        def add_arguments(self, parser: argparse.ArgumentParser):
            group = parser.add_argument_group('Keyboard')
            group.add_argument('-l', '--keyboard-layout', metavar='FILE', default='keyboard.conf',
                               help='Keyboard layout file, defaults to keyboard.conf')
            group.add_argument('--verbose-layout', action='store_true',
                               help='Include action descriptions')

        def __call__(self, args, app: Application = None):
            self._configurator.save_default_layout(args.keyboard_layout, args.verbose_layout)

    def layout_from_args(self, args) -> KeyboardLayout:
        """
        Create a keyboard layout. Use this to construct an instance of the KeyboardHandler subclass this configurator
        was created from.
        """
        if os.path.isfile(args.keyboard_layout):
            return self.load_layout(args.keyboard_layout)
        else:
            return self.default_layout()

    def _validate_actions(self):
        if len(self._actions) == 0:
            return
        # noinspection PyArgumentList
        counter = collections.Counter((action.name for action in self._actions))
        action, count = counter.most_common(1)[0]
        if count > 1:
            raise ConfigurationError(f'Duplicate keyboard action {action}')

    def load_layout(self, path: str) -> KeyboardLayout:
        logger = logwood.get_logger(self.__class__.__name__)
        bindings_by_action = {}
        with open(path) as f:
            for raw_line in f:
                line, *_ = raw_line.split('#')
                if not line.strip():
                    continue
                action, *bindings = line.split()
                if action in bindings_by_action:
                    raise ConfigurationError(f'Duplicate action {action}')
                bindings_by_action[action] = bindings

        actions_by_key = {}
        actions_by_scancode = {}
        for action in self._actions:
            if action.name not in bindings_by_action:
                logger.warning(f'Missing keybindings for action {action.name}')
            else:
                bindings = bindings_by_action.pop(action.name)
                self._parse_bindings_for_action(actions_by_key, actions_by_scancode, action.name, bindings)
        for action_name in bindings_by_action:
            logger.warning(f'Extra keybindings for unknown action {action_name}')
        return KeyboardLayout(actions_by_key=actions_by_key, actions_by_scancode=actions_by_scancode)

    def default_layout(self) -> KeyboardLayout:
        actions_by_key = {}
        actions_by_scancode = {}
        for action in self._actions:
            self._parse_bindings_for_action(actions_by_key, actions_by_scancode, action.name, action.defaults)
        return KeyboardLayout(actions_by_key=actions_by_key, actions_by_scancode=actions_by_scancode)

    def save_default_layout(self, path: str, verbose: bool = False):
        lines = []
        max_name_length = 0
        max_bindings_length = 0
        for action in self._actions:
            max_name_length = max(max_name_length, len(action.name))
            bindings = ' '.join(action.defaults)
            max_bindings_length = max(max_bindings_length, len(bindings))
            if verbose and action.description:
                description = '# ' + action.description
            else:
                description = None
            lines.append((action.name, bindings, description))

        max_name_length += 4 - (max_name_length % 4)
        max_bindings_length += 4 - (max_bindings_length % 4)
        with open(path, 'w') as f:
            for action_name, bindings, description in lines:
                if description:
                    f.write(f'{action_name:{max_name_length}s}{bindings:{max_bindings_length}s}{description}\n')
                elif bindings:
                    f.write(f'{action_name:{max_name_length}s}{bindings}\n')
                else:
                    f.write(f'{action_name}\n')

    @classmethod
    def _parse_bindings_for_action(cls, actions_by_key, actions_by_scancode, action: str, bindings: List[str]):
        for binding in bindings:
            code, is_scancode = cls._parse_binding(binding)
            if code is not None and is_scancode:
                if code in actions_by_scancode:
                    raise ConfigurationError(f'Binding {binding} -> {actions_by_scancode[code]} already exists, '
                                             f'cannot map to {action}')
                actions_by_scancode[code] = action
            elif code is not None and not is_scancode:
                if code in actions_by_key:
                    raise ConfigurationError(f'Binding {binding} -> {actions_by_key[code]} already exists, '
                                             f'cannot map to {action}')
                actions_by_key[code] = action

    @classmethod
    def _parse_binding(cls, binding: str) -> Tuple[int, bool]:
        if binding.startswith('sc_'):
            try:
                scancode = int(binding[3:])
                return scancode, True
            except ValueError:
                pass

        key = vars(pygame).get('K_' + binding, None)
        if key is None:
            raise ConfigurationError(f'Invalid keybinding {binding}')
        return key, False


class KeyboardHandler(SubComponent):
    ACTIONS = []
    COMPLETE_CAPTURE = [pygame.K_RETURN, pygame.K_KP_ENTER]
    BACK = [pygame.K_BACKSPACE]
    REPEAT_DELAY_MS = 500
    REPEAT_INTERVAL_MS = 50

    @classmethod
    def configurator(cls) -> KeyboardConfigurator:
        """
        Returns a KeyboardConfigurator, which should be registered via add_configurator in the application launcher.
        """
        return KeyboardConfigurator(actions=cls.ACTIONS)

    def __init__(self, layout: KeyboardLayout):
        self._layout = layout
        self._pressed = {}
        self._capture = False  # type: bool
        self._capture_id = None  # type: str
        self._capture_text = None  # type: str
        self._capture_completed = False  # type: bool

    def push_key_down(self, key: int, scancode: int, character: str) -> None:
        """
        This method is used by the framework to push KEYDOWN events to the handler.
        You should not need to call this method from your production code.
        """
        if self._capture:
            if key in self.COMPLETE_CAPTURE:
                self.text_capture_completed(self._capture_id, self._capture_text)
                self._capture = False
                self._capture_completed = True
                pygame.key.set_repeat()
            elif key in self.BACK:
                if len(self._capture_text):
                    self._capture_text = self._capture_text[:-1]
                    self.text_capture_update(self._capture_id, self._capture_text)
            else:
                self._capture_text += character
                self.text_capture_update(self._capture_id, self._capture_text)
        else:
            action = self._layout.action_by_key_or_scancode(key, scancode)
            if action:
                self._pressed[action] = True
                self.key_down(action)

    def push_key_up(self, key: int, scancode: int) -> None:
        """
        This method is used by the framework to push KEYUP events to the handler.
        You should not need to call this method from your production code.
        """
        if self._capture_completed and key in self.COMPLETE_CAPTURE:
            self._capture_completed = False
        elif not self._capture:
            action = self._layout.action_by_key_or_scancode(key, scancode)
            if action:
                self._pressed[action] = False
                self.key_up(action)

    def capture_text(self, capture_id: str, initial=''):
        """
        Trigger the capture of a single-line string. Capturing ends when RETURN is pressed.
        The result, together with the capture_id, is passed to the text function.
        As a side-effect, artificial key_up events are triggered for all active actions and their state is set to up.
        """
        # noinspection PyArgumentList
        pygame.key.set_repeat(self.REPEAT_DELAY_MS, self.REPEAT_INTERVAL_MS)
        self._capture = True
        self._capture_id = capture_id
        self._capture_text = initial
        for action in self._pressed:
            if self._pressed[action]:
                self._pressed[action] = False
                self.key_up(action)
        self.text_capture_update(self._capture_id, self._capture_text)

    def text_capture_completed(self, capture_id: str, text: str):
        """
        Override this method to receive captured text.
        """

    def text_capture_update(self, capture_id: str, text: str):
        """
        Override this method to receive changes to the currently captured text.
        """

    def is_pressed(self, action: str) -> bool:
        """
        Query the current state of a keyboard action
        """
        return self._pressed.get(action)

    def key_down(self, action: str) -> None:
        """
        Called after a KEYDOWN event for the associated key has been received by pygame
        """
        raise NotImplementedError

    def key_up(self, action: str) -> None:
        """
        Called after a KEYUP event for the associated key has been received by pygame
        """
        raise NotImplementedError

    def process(self) -> None:
        """
        Called after all pending keyboard events in the current iteration have been processed.
        Especially, this method is called after the key_down & key_up methods were called.
        This method is the place to trigger actions based on the state of actions that can be queried via the
        is_pressed method.
        """
        raise NotImplementedError


class KeyboardEvent(NamedTuple):
    action: str
    active: bool


class CaptureTextEvent(NamedTuple):
    capture_id: str
    text: str
    complete: bool


class EventBasedKeyboardHandler(KeyboardHandler):

    CAPTURE_TEXT_TRIGGER = 'async2v.keyboard.trigger.capture'
    CAPTURE_TEXT_EVENT = 'async2v.keyboard.text'
    KEYBOARD_EVENT = 'async2v.keyboard.action'

    def __init__(self, layout: KeyboardLayout):
        super().__init__(layout)
        self.keyboard = Output(self.KEYBOARD_EVENT)
        self.text = Output(self.KEYBOARD_EVENT)
        self.capture_trigger = Latest(self.CAPTURE_TEXT_TRIGGER)

    def key_down(self, action: str) -> None:
        self.keyboard.push(KeyboardEvent(action, True))

    def key_up(self, action: str) -> None:
        self.keyboard.push(KeyboardEvent(action, False))

    def process(self) -> None:
        if self.capture_trigger.updated:
            self.capture_text(self.capture_trigger.value)

    def text_capture_update(self, capture_id: str, text: str):
        self.text.push(CaptureTextEvent(capture_id, text, complete=False))

    def text_capture_completed(self, capture_id: str, text: str):
        self.text.push(CaptureTextEvent(capture_id, text, complete=True))


class NoOpKeyboardHandler(KeyboardHandler):
    def __init__(self):
        super().__init__(KeyboardLayout({}, {}))

    def key_down(self, action: str) -> None:
        pass

    def key_up(self, action: str) -> None:
        pass

    def handle(self) -> None:
        pass

    def process(self) -> None:
        pass
