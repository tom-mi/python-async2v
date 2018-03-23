import re
from typing import Tuple, NamedTuple, Optional, List, Callable, Union

import logwood
import pygame


class DisplayConfiguration(NamedTuple):
    resolution: Optional[Tuple[int, int]]
    fullscreen: bool

    def __str__(self):
        if self.fullscreen:
            mode = 'fullscreen'
        else:
            mode = 'window'
        return f'{self.resolution[0]}x{self.resolution[1]} {mode}'


DEFAULT_CONFIG = DisplayConfiguration((800, 600), False)
DEFAULT_FULLSCREEN_CONFIG = DisplayConfiguration(None, True)


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
        config = DisplayConfiguration(resolution, config.fullscreen)

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


def best_regular_screen_layout(src_frames: List[Tuple[int, int]], target: Tuple[int, int]) -> Tuple[int, int]:
    possible_layouts = possible_screen_layouts(len(src_frames))
    best_layout = None
    best_ratio = 0
    for layout in possible_layouts:
        sub_frame_target = (int(target[0] / layout[0]), int(target[1] / layout[1]))
        screen_coverage = 0
        for frame in src_frames:
            _, resized = scale_and_center_preserving_aspect(frame, sub_frame_target)
            screen_coverage += resized[0] * resized[1]

        ratio = screen_coverage / (target[0] * target[1])
        if ratio > best_ratio:
            best_layout = layout
            best_ratio = ratio
    return best_layout


def possible_screen_layouts(number_of_frames: int) -> List[Tuple[int, int]]:
    possible_layouts = []
    best_n_y = number_of_frames + 1
    for n_x in range(1, number_of_frames + 1):
        for n_y in range(1, best_n_y):
            if n_x * n_y >= number_of_frames:
                best_n_y = n_y
                possible_layouts.append((n_x, n_y))
                break

    return possible_layouts


def length_normalizer(size: Tuple[int, int], reference: int = 600) -> Callable[[Union[float, int]], int]:
    scale = min(size) / reference

    def normalize_to_int(value):
        return int(value * scale)

    return normalize_to_int
