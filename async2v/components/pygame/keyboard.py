"""
Pygame based keyboard input

This module provides an abstraction from the concrete key bindings by defining a keyboard handler based on actions.
Those actions can be mapped to arbitrary keys. A default mapping can be specified.
This module also comes with ready-to-use configurator & command line interface to perform common keyboard layout
management tasks like generating a default layout file or configuring the desired layout via command line switch.

Two base classes are available that can be overridden to provide an application with keyboard support,
`KeyboardHandler` and `EventBasedKeyboardHandler`.

Example for integrating a keyboard handler into an application:

::

    class MyKeyboardHandler(EventBasedKeyboardHandler):
        ACTIONS = [
            Action('run', ['UP', 'w']),
            Action('jump', ['SPACE']),
        ]

    class Launcher(ApplicationLauncher):

        def __init__(self):
            super().__init__()
            self.add_configurator(MyKeyboardHandler.configurator())
            self.add_configurator(MainWindow.configurator())

        def register_application_components(self, args, app: Application):
            # ...
            main_window_config = MainWindow.configurator().config_from_args(args)
            layout = MyKeyboardHandler.configurator().layout_from_args(args)
            keyboard = MyKeyboardHandler(layout)
            # ...
            main = MainWindow([display], keyboard_handler=keyboard, config=main_window_config)
            app.register(main)
"""

import argparse
import collections
import os.path
from dataclasses import dataclass
from typing import List, Dict, Tuple

import logwood
import pygame

from async2v.application import Application
from async2v.cli import Configurator, Command
from async2v.components.base import SubComponent
from async2v.error import ConfigurationError
from async2v.fields import Output, Latest


class Action:
    """
    Keyboard action
    """

    def __init__(self, name: str, defaults: List[str] = None, description: str = None):
        """
        :param name: Name of the keyboard action (must not contain whitespace)
        :param defaults: Default keybindings for this action
        :param description:
        """
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


@dataclass
class KeyboardLayout:
    """
    Concrete mapping from keys to actions

    Do not instantiate this class directly, but create it via the matching `KeyboardConfigurator`.
    """
    actions_by_key: Dict[int, str]
    actions_by_scancode: Dict[int, str]
    help: List[Tuple[str, str]]

    def action_by_key_or_scancode(self, key: int, scancode: int) -> str:
        result = self.actions_by_key.get(key, None)
        if result:
            return result
        return self.actions_by_scancode.get(scancode, None)


class KeyboardConfigurator(Configurator):
    """
    Configurator for subclasses of `KeyboardHandler`

    Do not instantiate this class directly, but create it from a subclass of `KeyboardHandler` via the
    `configurator <async2v.components.pygame.keyboard.KeyboardHandler.configurator>` class method.
    """

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
        Create a keyboard layout. Use this to construct an instance of the `KeyboardHandler` subclass this configurator
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
        help_texts = []
        for action in self._actions:
            if action.name not in bindings_by_action:
                logger.warning(f'Missing keybindings for action {action.name}')
                help_texts.append((action.description or action.name, '<unassigned>'))
            else:
                bindings = bindings_by_action.pop(action.name)
                help_texts.append((action.description or action.name, ', '.join(bindings) or '<unassigned>'))
                self._parse_bindings_for_action(actions_by_key, actions_by_scancode, action.name, bindings)
        for action_name in bindings_by_action:
            logger.warning(f'Extra keybindings for unknown action {action_name}')
        return KeyboardLayout(actions_by_key=actions_by_key, actions_by_scancode=actions_by_scancode, help=help_texts)

    def default_layout(self) -> KeyboardLayout:
        actions_by_key = {}
        actions_by_scancode = {}
        help_texts = []
        for action in self._actions:
            help_texts.append((action.description or action.name, ', '.join(action.defaults) or '<unassigned>'))
            self._parse_bindings_for_action(actions_by_key, actions_by_scancode, action.name, action.defaults)
        return KeyboardLayout(actions_by_key=actions_by_key, actions_by_scancode=actions_by_scancode, help=help_texts)

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
    """
    Abstract keyboard handler base class

    Override this class to implement advanced keyboard handling. For most use cases, `EventBasedKeyboardHandler`
    should be sufficient.

    Example:

    ::

        class MyKeyboardHandler(KeyboardHandler):
            ACTIONS = [
                Action('left', ['a']),
                Action('right', ['d']),
            ]

            def __init__(self, layout: KeyboardLayout):
                super().__init__(layout)
                self.output = Output('output')

            def key_down(self, action: str) -> None:
                self.output.push(['ping', action])

            def key_up(self, action: str) -> None:
                self.output.push(['pong', action])

            def process(self) -> None:
                pass
    """
    ACTIONS: List[Action] = []
    """
    :type: List[Action]

    Needs to be overwritten in subclass to specify the keyboard actions for thta layout
    """

    COMPLETE_CAPTURE: List[int] = [pygame.K_RETURN, pygame.K_KP_ENTER]
    """
    :type: List[int]

    Can be overwritten to change the keys completing text capture (see `capture_text`)
    """

    BACK: List[int] = [pygame.K_BACKSPACE]
    """
    :type: List[int]

    Can be overwritten to change the keys removing the last character from text capture (see `capture_text`)
    """

    REPEAT_DELAY_MS: int = 500
    """
    :type: int

    Can be overwritten to change the delay before keys are repeated on long key press during text capture
    (see `capture_text`)
    """

    REPEAT_INTERVAL_MS: int = 50
    """
    :type: int

    Can be overwritten to change the interval at which keys are repeated on long key press during text capture
    (see `capture_text`)
    """

    @classmethod
    def configurator(cls) -> KeyboardConfigurator:
        """
        Create a configurator for the keyboard `ACTIONS` specified in the concrete handler
        """
        return KeyboardConfigurator(actions=cls.ACTIONS)

    def __init__(self, layout: KeyboardLayout):
        """
        :param layout: Use layout created by the `layout_from_args` method of the `KeyboardConfigurator` created for
            that concrete `KeyboardHandler`
        """
        self._layout = layout
        self._pressed = {}
        self._capture: bool = False
        self._capture_id: str = None
        self._capture_text: str = None
        self._capture_completed: bool = False

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


@dataclass
class KeyboardEvent:
    """
    Keyboard event denoting the state change of a `Action`
    """

    action: str
    """
    :type: str

    Keyboard action name as defined in the corresponding `Action`
    """

    active: bool
    """
    :type: bool

    `True` if the key mapped to this action is pressed
    """


@dataclass
class CaptureTextEvent:
    """
    Keyboard event denoting the current capture state of text

    Capturing text is triggered by calling `capture_text` on the keyboard handler.
    """

    capture_id: str
    """
    :type: str

    Capture ide passed to `capture_text`
    """

    text: str
    """
    :type: str

    Captured text so far
    """

    complete: bool
    """
    :type: bool

    `True` iff this text capture flow is complete (in that case, `text` contains the complete text)
    """


class EventBasedKeyboardHandler(KeyboardHandler):
    """
    Abstract event based keyboard handler base class

    This keyboard handler emits events containing `KeyboardEvent` payload on the event key `KEYBOARD_EVENT`, when a key
    bound to a configured `Action` is pressed or released.

    Text capture can be triggered by sending an event containing a `capture_id` to the key `CAPTURE_TEXT_TRIGGER`.
    The results of this text capture flow are emitted via events containing `CaptureTextEvent` payload on the event key
    `CAPTURE_TEXT_EVENT`.

    Example:

    ::

        class MyKeyboardHandler(EventBasedKeyboardHandler):
            ACTIONS = [
                Action('up', ['UP', 'w']),
                Action('down', ['DOWN', 's']),
                Action('left', ['LEFT', 'a']),
                Action('right', ['RIGHT', 'd']),
            ]

    """

    CAPTURE_TEXT_TRIGGER: str = 'async2v.keyboard.trigger.capture'
    """
    :type: str
    """

    CAPTURE_TEXT_EVENT: str = 'async2v.keyboard.text'
    """
    :type: str
    """

    KEYBOARD_EVENT: str = 'async2v.keyboard.action'
    """
    :type: str
    """

    def __init__(self, layout: KeyboardLayout):
        """
        :param layout: Use layout created by the `layout_from_args` method of the `KeyboardConfigurator` created for
            that concrete `KeyboardHandler`
        """
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


class _NoOpKeyboardHandler(KeyboardHandler):
    def __init__(self):
        super().__init__(KeyboardLayout({}, {}, []))

    def key_down(self, action: str) -> None:
        pass

    def key_up(self, action: str) -> None:
        pass

    def handle(self) -> None:
        pass

    def process(self) -> None:
        pass
