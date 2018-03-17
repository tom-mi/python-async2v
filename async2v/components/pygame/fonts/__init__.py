import os.path
import pygame.freetype

pygame.freetype.init()

_root = os.path.dirname(os.path.realpath(__file__))

BEDSTEAD = pygame.freetype.Font(os.path.join(_root, 'bedstead.otf'))
