import re
from typing import Tuple, Callable, Union


def parse_resolution(value: str) -> Tuple[int, int]:
    """
    Parse a resolution string of the format WIDTHxHEIGHT to a tuple (width, height).

    :param value: Input string of the format WIDTHxHEIGHT. Only integral values are supported.
    """
    m = re.match(r'^(\d+)x(\d+)$', value)
    if not m:
        raise ValueError(f'Invalid resolution {value}')
    return int(m.group(1)), int(m.group(2))


def length_normalizer(size: Tuple[int, int], reference: int = 600) -> Callable[[Union[float, int]], int]:
    """
    Scale lengths according to screen resolution

    Returns a function that scales lengths according to the given screen size based on a reference value.
    This allows to easily define lengths in a readable way independent from the actual screen resolution.

    Example usage:
        >>> s = length_normalizer(surface.get_size())
        >>> render_hud_text(surface, 'Hello!', size=s(60))
        >>> render_hud_text(surface, 'World!', size=s(40), position=(1, 0))

    :param size: Screen size (width, height)
    :param reference: Reference screen size (short edge, usually height)
    :return: Function that returns scaled size as `int`
    """
    scale = min(size) / reference

    def normalize_to_int(value):
        return int(value * scale)

    return normalize_to_int
