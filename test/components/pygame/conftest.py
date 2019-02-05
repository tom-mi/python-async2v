import pygame
import pytest


@pytest.fixture
def pygame_video(monkeypatch):
    monkeypatch.setenv('SDL_VIDEODRIVER', 'dummy')
    pygame.display.init()  # required as pygame.key.set_repeat() is called in tested code
