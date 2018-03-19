import textwrap

import pygame
import pytest
from async2v.components.pygame.keyboard import Action, KeyboardConfigurator, KeyboardHandler, KeyboardLayout
from async2v.error import ConfigurationError


@pytest.fixture
def config():
    return KeyboardConfigurator([
        Action('forward', defaults=['w'], description='Move forward'),
        Action('backward', defaults=['DOWN', 'sc_39']),
        Action('left', defaults=[]),
    ])


@pytest.fixture
def layout_file(tmpdir):
    file = tmpdir.join('keyboard.conf')
    file.write(textwrap.dedent('''
        forward UP KP8
        left    sc_38   # this is a comment
            # empty        
            
        sideways LEFT
    ''').strip())
    return str(file)


@pytest.mark.parametrize('key, scancode, expected_action', [
    (pygame.K_w, 0, 'forward'),
    (pygame.K_DOWN, 0, 'backward'),
    (pygame.K_w, 39, 'forward'),
    (0, 39, 'backward'),
    (0, 40, None),
    (pygame.K_s, 0, None),
])
def test_default_layout(config: KeyboardConfigurator, key, scancode, expected_action):
    layout = config.default_layout()

    assert layout.action_by_key_or_scancode(key, scancode) == expected_action


@pytest.mark.parametrize('key, scancode, expected_action', [
    (pygame.K_w, 0, None),
    (0, 39, None),
    (pygame.K_UP, 0, 'forward'),
    (pygame.K_KP8, 0, 'forward'),
    (0, 38, 'left'),
])
def test_load_layout(config: KeyboardConfigurator, layout_file, key, scancode, expected_action):
    layout = config.load_layout(layout_file)

    assert layout.action_by_key_or_scancode(key, scancode) == expected_action


@pytest.mark.parametrize('binding', ['A', 'K_a', 'sc_', 'sc_1x'])
def test_default_layout_fails_to_parse_for_invalid_bindings(binding):
    with pytest.raises(ConfigurationError):
        KeyboardConfigurator([Action('foo', defaults=[binding])]).default_layout()


@pytest.mark.parametrize('actions', [
    ([Action('foo', defaults=['a', 'a'])]),
    ([Action('foo', defaults=['sc_1', 'sc_1'])]),
    ([Action('foo', defaults=['a']), Action('bar', defaults=['a'])]),
    ([Action('foo', defaults=['sc_1']), Action('bar', defaults=['sc_1'])]),
])
def test_default_layout_fails_for_duplicate_mappings(actions):
    with pytest.raises(ConfigurationError):
        KeyboardConfigurator(actions).default_layout()


def test_fails_on_duplicate_action():
    with pytest.raises(ConfigurationError):
        KeyboardConfigurator([Action('foo'), Action('foo')])


def test_save_default_layout(config: KeyboardConfigurator, tmpdir):
    target = tmpdir.join('keyboard_layout.conf')
    config.save_default_layout(str(target))

    expected_content = textwrap.dedent('''
        forward     w
        backward    DOWN sc_39
        left
    ''').strip() + '\n'

    assert target.read() == expected_content


def test_save_default_layout_verbose(config: KeyboardConfigurator, tmpdir):
    target = tmpdir.join('keyboard_layout.conf')
    config.save_default_layout(str(target), verbose=True)

    expected_content = textwrap.dedent('''
        forward     w           # Move forward
        backward    DOWN sc_39
        left
    ''').strip() + '\n'

    content = target.read()

    assert content == expected_content


def test_keyboard_handler():
    configurator = MyKeyboardHandler.configurator()
    layout = configurator.default_layout()
    handler = MyKeyboardHandler(layout)

    handler.push_event(pygame.K_w, 0, True)
    assert handler.is_pressed('forward')
    assert not handler.is_pressed('backward')
    handler.push_event(pygame.K_w, 0, False)
    handler.push_event(0, 39, True)
    assert not handler.is_pressed('forward')
    assert handler.is_pressed('backward')
    handler.push_event(0, 39, False)

    assert handler.log == ['forward_down', 'forward_up', 'backward_down', 'backward_up']


class MyKeyboardHandler(KeyboardHandler):
    ACTIONS = [
        Action('forward', ['w', 'sc_25']),
        Action('left', ['a', 'sc_38']),
        Action('backward', ['s', 'sc_39']),
        Action('right', ['d', 'sc_40']),
    ]

    def __init__(self, layout: KeyboardLayout):
        super().__init__(layout)
        self.log = []

    def key_down(self, action: str) -> None:
        self.log.append(action + '_down')

    def key_up(self, action: str) -> None:
        self.log.append(action + '_up')

    def process(self) -> None:
        pass
