from enum import Enum, auto
from typing import NamedTuple, Tuple, Dict, List, Optional

import pygame

from async2v.components.base import SubComponent
from async2v.fields import Output

ROOT_REGION = 'screen'


class MouseButton(Enum):
    LEFT = 1
    MIDDLE = 2
    RIGHT = 3
    WHEEL_UP = 4
    WHEEL_DOWN = 5


class MouseEventType(Enum):
    UP = auto()
    DOWN = auto()
    ENTER = auto()
    LEAVE = auto()


class MouseRegion(NamedTuple):
    name: str
    rect: pygame.Rect
    original_size: Tuple[int, int]


class MouseMovement(NamedTuple):
    region: MouseRegion
    position: Tuple[int, int]
    movement: Tuple[int, int]
    buttons: Dict[MouseButton, bool]

    @property
    def relative_position(self) -> Tuple[int, int]:
        return self.position[0] - self.region.rect.x, self.position[1] - self.region.rect.y

    @property
    def normalized_position(self) -> Tuple[float, float]:
        x, y = self.relative_position
        return x / self.region.rect.width, y / self.region.rect.height

    @property
    def restored_position(self) -> Tuple[int, int]:
        x_n, y_n = self.normalized_position
        w, h = self.region.original_size
        return int(x_n * w), int(y_n * h)


class MouseEvent(NamedTuple):
    # TODO check if some of the duplication can be removed with future (or present) python features
    region: MouseRegion
    position: Tuple[int, int]
    event_type: MouseEventType
    button: MouseButton = None

    @property
    def relative_position(self) -> Tuple[int, int]:
        return self.position[0] - self.region.rect.x, self.position[1] - self.region.rect.y

    @property
    def normalized_position(self) -> Tuple[float, float]:
        x, y = self.relative_position
        return x / self.region.rect.width, y / self.region.rect.height


class MouseHandler(SubComponent):

    def push_regions(self, regions: [MouseRegion]):
        """
        This method is used by the framework to push the current regions to the handler.
        You should not need to call this method from your production code.
        You need to override this method when implementing the MouseHandler.
        """
        raise NotImplementedError

    def push_button_down(self, position: Tuple[int, int], button: int):
        """
        This method is used by the framework to push a MOUSEBUTTONDOWN event to the handler.
        You should not need to call this method from your production code.
        You need to override this method when implementing the MouseHandler.
        """
        raise NotImplementedError

    def push_button_up(self, position: Tuple[int, int], button: int):
        """
        This method is used by the framework to push a MOUSEBUTTONUP event to the handler.
        You should not need to call this method from your production code.
        You need to override this method when implementing the MouseHandler.
        """
        raise NotImplementedError

    def push_movement(self, position: Tuple[int, int], rel: Tuple[int, int], buttons: Tuple[int, int, int]):
        """
        This method is used by the framework to push a MOUSEMOTION event to the handler.
        You should not need to call this method from your production code.
        You need to override this method when implementing the MouseHandler.
        """
        raise NotImplementedError


class EventBasedMouseHandler(MouseHandler):
    MOUSE_EVENT = 'async2v.mouse.event'
    MOUSE_MOVEMENT = 'async2v.mouse.movement'

    def __init__(self):
        self._regions = []  # type: List[MouseRegion]
        self.event = Output(self.MOUSE_EVENT)
        self.movement = Output(self.MOUSE_MOVEMENT)
        self._last_region = None  # type: MouseRegion
        self._last_position = (-1, -1)

    def push_regions(self, regions: [MouseRegion]):
        self._regions = regions  # type: List[MouseRegion]
        self._get_region()

    def _get_region(self, position: Tuple[int, int] = None) -> Optional[MouseRegion]:
        if position:
            self._last_position = position
        for region in reversed(self._regions):
            if region.rect.collidepoint(self._last_position[0], self._last_position[1]):
                if not self._last_region or region.name != self._last_region.name:
                    if self._last_region:
                        self.event.push(MouseEvent(self._last_region, self._last_position, MouseEventType.LEAVE))
                    self.event.push(MouseEvent(region, self._last_position, MouseEventType.ENTER))
                    self._last_region = region
                return region
        else:
            if self._last_position != (-1, -1):
                self.logger.warning(f'Position {self._last_position} is not in any region')
            return None

    def push_button_down(self, position: Tuple[int, int], button: int):
        region = self._get_region(position)
        button = MouseButton(button)
        if region:
            self.event.push(MouseEvent(region, position, MouseEventType.DOWN, button=button))

    def push_button_up(self, position: Tuple[int, int], button: int):
        region = self._get_region(position)
        button = MouseButton(button)
        if region:
            self.event.push(MouseEvent(region, position, MouseEventType.UP, button=button))

    def push_movement(self, position: Tuple[int, int], rel: Tuple[int, int], buttons: Tuple[int, int, int]):
        region = self._get_region(position)
        buttons = {MouseButton(i + 1): buttons[i] > 0 for i in range(3)}
        if region:
            self.movement.push(MouseMovement(region, position, rel, buttons))


class NoOpMouseHandler(MouseHandler):

    def push_regions(self, regions: [MouseRegion]):
        pass

    def push_button_down(self, position: Tuple[int, int], button: int):
        pass

    def push_button_up(self, position: Tuple[int, int], button: int):
        pass

    def push_movement(self, position: Tuple[int, int], rel: Tuple[int, int], buttons: Tuple[int, int, int]):
        pass
