"""
Pygame based mouse input

For most use cases, the `EventBasedMouseHandler` is sufficient.
It emits two kinds of mouse events, `MouseMovement` and `MouseEvent`. Those events include a `MouseRegion` where the
event occurred. There is always at least one region, ``screen``, which covers the whole screen.
Additional regions can be returned from the `draw <async2v.components.pygame.display.Display.draw>`
method of displays. This is especially required for the `Button` from the `gui` module to handle click events.

When a new mouse event is received from pygame, the list of regions is searched in reverse order. The first region that
contains the location of the mouse event is then passed with the emitted `MouseMovement` or `MouseEvent` event.

The root region, ``screen``, is always the last resort if no other region matched before.

Some builtin display components (e.g. `OpenCvDisplay` or `OpenCvMultiDisplay`) also provide regions other than the
root region.

The `EventBasedMouseHandler` needs no configuration, it just needs to be passed to the `MainWindow`:

::

    class Launcher(ApplicationLauncher):

        def __init__(self):
            super().__init__()
            self.add_configurator(MainWindow.configurator())

        def register_application_components(self, args, app: Application):
            main_window_config = MainWindow.configurator().config_from_args(args)
            mouse_handler = EventBasedMouseHandler()
            displays = [
                OpenCvDebugDisplay(),
            ]
            main_window = MainWindow(displays, config=main_window_config, mouse_handler=mouse_handler)
            app.register(main_window)

For special use cases, the abstract `MouseHandler` can be implemented and used instead. Note that in this case you
need to implement region handling yourself (if you require it).
"""
from dataclasses import dataclass
from enum import Enum, auto
from typing import Tuple, Dict, List, Optional

import pygame

from async2v.components.base import SubComponent
from async2v.fields import Output

ROOT_REGION = 'screen'


class MouseButton(Enum):
    """ """
    LEFT = 1  #:
    MIDDLE = 2  #:
    RIGHT = 3  #:
    WHEEL_UP = 4  #:
    WHEEL_DOWN = 5  #:
    BUTTON_6 = 6  #:
    BUTTON_7 = 7  #:
    BUTTON_8 = 8  #:
    BUTTON_9 = 9  #:


class MouseEventType(Enum):
    """ """
    UP = auto()  #: Mouse up
    DOWN = auto()  #: Mouse down
    ENTER = auto()  #: Mouse enters region
    LEAVE = auto()  #: Mouse leaves region


@dataclass
class MouseRegion:
    """
    Rectangular area on the screen capturing mouse events
    """

    name: str
    """
    :type: str
    """

    rect: pygame.Rect
    """
    :type: pygame.Rect

    Location of the mouse region on pygame surface
    """

    original_size: Tuple[int, int]
    """
    :type: Tuple[int, int]

    Reference dimensions (width, height) to calculate mouse positions to (e.g. in coordinates of drawn OpenCV image)
    """

    def move(self, x: int, y: int) -> 'MouseRegion':
        return MouseRegion(self.name, self.rect.move(x, y), self.original_size)


@dataclass
class MouseMovement:
    """
    Mouse movement event
    """

    region: MouseRegion
    """
    :type: MouseRegion

    Region this movement was registered on
    """

    position: Tuple[int, int]
    """
    :type: Tuple[int, int]

    Position in pixels on pygame surface
    """

    movement: Tuple[int, int]
    """
    :type: Tuple[int, int]

    Movement in pixels on pygame surface
    """

    buttons: Dict[MouseButton, bool]
    """
    :type: Dict[MouseButton, bool]

    State of all mouse buttons (`True` for pressed buttons)
    """

    @property
    def relative_position(self) -> Tuple[int, int]:
        """
        Position in pixels within `region`
        """
        return self.position[0] - self.region.rect.x, self.position[1] - self.region.rect.y

    @property
    def normalized_position(self) -> Tuple[float, float]:
        """
        Position within `region`, normalized to coordinates between 0 and 1
        """
        x, y = self.relative_position
        return x / self.region.rect.width, y / self.region.rect.height

    @property
    def restored_position(self) -> Tuple[int, int]:
        """
        Position within `region`, normalized to the dimensions given in `original_size`
        """
        x_n, y_n = self.normalized_position
        w, h = self.region.original_size
        return int(x_n * w), int(y_n * h)


@dataclass
class MouseEvent:
    # TODO check if some of the duplication can be removed with future (or present) python features
    region: MouseRegion
    """
    :type: MouseRegion

    Region this movement was registered on
    """

    position: Tuple[int, int]
    """
    :type: Tuple[int, int]

    Position in pixels on pygame surface
    """

    event_type: MouseEventType
    """
    :type: MouseEventType
    """

    button: MouseButton = None
    """
    :type: MouseButton

    Button that was pressed or released if `event_type` is `UP` or `DOWN`, `None` otherwise
    """

    @property
    def relative_position(self) -> Tuple[int, int]:
        """
        Position in pixels within `region`
        """
        return self.position[0] - self.region.rect.x, self.position[1] - self.region.rect.y

    @property
    def normalized_position(self) -> Tuple[float, float]:
        """
        Position within `region`, normalized to coordinates between 0 and 1
        """
        x, y = self.relative_position
        return x / self.region.rect.width, y / self.region.rect.height

    @property
    def restored_position(self) -> Tuple[int, int]:
        """
        Position within `region`, normalized to the dimensions given in `original_size`
        """
        x_n, y_n = self.normalized_position
        w, h = self.region.original_size
        return int(x_n * w), int(y_n * h)


class MouseHandler(SubComponent):
    """
    Abstract mouse handler base class

    Override this class to implement advanced mouse handling. For most use cases, `EventBasedMouseHandler`
    should be sufficient.
    """

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
    """
    Event based mouse handler

    This mouse handler emits events containing `MouseEvent` payload on the event key `MOUSE_EVENT` and
    events containing `MouseMovement` payload on the event key `MOUSE_MOVEMENT`.

    Supports the `MouseRegion` concept explained above.
    """

    MOUSE_EVENT: str = 'async2v.mouse.event'
    """
    :type: str
    """

    MOUSE_MOVEMENT: str = 'async2v.mouse.movement'
    """
    :type: str
    """

    def __init__(self):
        self._regions: List[MouseRegion] = []
        self.event = Output(self.MOUSE_EVENT)
        self.movement = Output(self.MOUSE_MOVEMENT)
        self._last_region: MouseRegion = None
        self._last_position = (-1, -1)

    def push_regions(self, regions: [MouseRegion]):
        self._regions: List[MouseRegion] = regions
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


class _NoOpMouseHandler(MouseHandler):

    def push_regions(self, regions: [MouseRegion]):
        pass

    def push_button_down(self, position: Tuple[int, int], button: int):
        pass

    def push_button_up(self, position: Tuple[int, int], button: int):
        pass

    def push_movement(self, position: Tuple[int, int], rel: Tuple[int, int], buttons: Tuple[int, int, int]):
        pass
