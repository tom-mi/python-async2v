import asyncio
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


async def run_in_executor(func: Callable, *args) -> asyncio.Future:
    """
    Run a function in a thread pool executor.

    This is a convenience wrapper for ``asyncio.get_event_loop().run_in_executor(...)``.

    Use this within your components to allow the main loop to continue during expensive operations, for example:

    ::

        async def process(self):
            result = await run_in_executor(self._expensive_operation, self.input.value.image)
            self.output.push(result)

    See `asyncio.loop.run_in_executor` for more information.

    :param func: Expensive function or method that shall run outside the main loop
    :param args: Arguments to pass to ``func``
    :return: Future that will contain the to the return value of ``func`` as a result
    """
    return await asyncio.get_event_loop().run_in_executor(None, func, *args)
