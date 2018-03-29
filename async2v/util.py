import re
from typing import Tuple, Callable, Union


def parse_resolution(value: str) -> Tuple[int, int]:
    m = re.match(r'^(\d+)x(\d+)$', value)
    if not m:
        raise ValueError(f'Invalid resolution {value}')
    return int(m.group(1)), int(m.group(2))


def length_normalizer(size: Tuple[int, int], reference: int = 600) -> Callable[[Union[float, int]], int]:
    scale = min(size) / reference

    def normalize_to_int(value):
        return int(value * scale)

    return normalize_to_int
