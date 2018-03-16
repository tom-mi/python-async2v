import re
from typing import Tuple, NamedTuple, Optional

import logwood
import pygame


class DisplayConfiguration(NamedTuple):
    resolution: Optional[Tuple[int, int]]
    fullscreen: bool
    resizable: bool

    def __str__(self):
        if self.fullscreen:
            mode = 'fullscreen'
        elif self.resizable:
            mode = 'resizable'
        else:
            mode = 'window'
        return f'{self.resolution[0]}x{self.resolution[1]} {mode}'


DEFAULT_CONFIG = DisplayConfiguration((800, 600), False, False)
DEFAULT_FULLSCREEN_CONFIG = DisplayConfiguration(None, True, False)


def list_resolutions():
    pygame.display.init()
    print('Available fullscreen resolutions:')
    for mode in pygame.display.list_modes():
        print(f'    {mode[0]}x{mode[1]}')


def configure_display(config: DisplayConfiguration) -> pygame.Surface:
    logger = logwood.get_logger('pygame')
    pygame.display.init()
    if config is None:
        config = DEFAULT_CONFIG
    resolution = config.resolution
    if resolution is None:
        if config.fullscreen:
            resolution = pygame.display.list_modes()[0]
        else:
            resolution = DEFAULT_CONFIG.resolution
        config = DisplayConfiguration(resolution, config.fullscreen, config.resizable)

    flags = _get_best_flags_for_config(config)
    logger.info(f'Setting display mode to {config}')
    return pygame.display.set_mode(resolution, flags)


def parse_resolution(value: str) -> Tuple[int, int]:
    m = re.match(r'^(\d+)x(\d+)$', value)
    if not m:
        raise ValueError(f'Invalid resolution {value}')
    return int(m.group(1)), int(m.group(2))


def _get_best_flags_for_config(config: DisplayConfiguration):
    logger = logwood.get_logger('pygame')
    if config.fullscreen:
        base_flags = pygame.FULLSCREEN
    elif config.resizable:
        base_flags = pygame.RESIZABLE
    else:
        base_flags = 0

    hw_accelerated_flags = pygame.HWACCEL | pygame.DOUBLEBUF | base_flags

    if pygame.display.mode_ok(config.resolution, hw_accelerated_flags):
        logger.info('Using hardware accelerated display')
        return hw_accelerated_flags
    elif pygame.display.mode_ok(config.resolution, base_flags):
        logger.info('Using software display')
        return base_flags
    else:
        raise RuntimeError(f'Display mode {config} is not supported')


def scale_and_center_preserving_aspect(src_resolution: Tuple[int, int],
                                       target_resolution: Tuple[int, int]) -> Tuple[Tuple[int, int], Tuple[int, int]]:
    width = min(target_resolution[0], int(target_resolution[1] / src_resolution[1] * src_resolution[0]))
    height = min(target_resolution[1], int(target_resolution[0] / src_resolution[0] * src_resolution[1]))
    offset_x = int((target_resolution[0] - width) / 2)
    offset_y = int((target_resolution[1] - height) / 2)
    return (offset_x, offset_y), (width, height)
