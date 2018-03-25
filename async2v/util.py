import re
from typing import Tuple


def parse_resolution(value: str) -> Tuple[int, int]:
    m = re.match(r'^(\d+)x(\d+)$', value)
    if not m:
        raise ValueError(f'Invalid resolution {value}')
    return int(m.group(1)), int(m.group(2))
