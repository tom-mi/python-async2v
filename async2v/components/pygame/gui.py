"""
Very simple and basic gui elements.

Gui elements have a fixed height and a minimal width. They can only be aligned in vertical stacked groups.
Afterwards, all elements are drawn with the same width, which is the width of the widest element.
"""
from typing import List, Tuple, Callable

import pygame.freetype

from async2v.components.pygame.fonts import BEDSTEAD
from async2v.components.pygame.mouse import MouseRegion, MouseEvent, MouseButton, MouseEventType

DEFAULT_MENU_BGCOLOR = (0, 0, 0, 128)
DEFAULT_FGCOLOR = (255, 255, 255)
DEFAULT_BUTTON_BGCOLOR = (64, 64, 64, 128)
DEFAULT_BUTTON_HLBGCOLOR = (128, 128, 128, 224)


class GuiElement:
    """
    Abstract base class for gui elements
    """

    @property
    def height(self) -> int:
        raise NotImplementedError

    @property
    def min_width(self) -> int:
        raise NotImplementedError

    def draw(self, surface: pygame.Surface) -> List[MouseRegion]:
        raise NotImplementedError

    def handle_mouse_event(self, event: MouseEvent):
        pass


class Menu:
    """
    Container for gui elements

    Handles positioning and drawing of a vertical list of gui elements, such as :py:class:`Label` or :py:class:`Button`.
    For buttons in the menu to be functional, mouse events need to be passed from the display drawing the menu.

    Example:

    ::

        class MyDisplay(OpenCvDisplay):

            def __init__(self, source):
                super().__init__(source)
                self.mouse_event: Buffer[MouseEvent] = Buffer(EventBasedMouseHandler.MOUSE_EVENT)
                self.menu = Menu([
                    Label('Menu'),
                    Button('Do something', self.handler),
                ], position=(1, 0))

            def handler(self):
                # do something

            def draw(self, surface: pygame.Surface) -> List[MouseRegion]:
                regions = super().draw(surface)
                self.menu.handle_mouse_events(self.mouse_event.values)
                regions += self.menu.draw(surface)
                return regions
    """

    def __init__(self, elements: List[GuiElement], position: Tuple[float, float] = (0, 0), bgcolor=DEFAULT_MENU_BGCOLOR,
                 padding: float = 4):
        """
        :param elements: Gui elements to render. Will be arranged vertically from top to bottom.
        :param position: Relative position within the display from (0, 0) to (1, 1). (0.5, 0.5) for center.
        :param bgcolor: Background color as RGB or RGBA
        :param padding: Padding, defaults to 4.
        """
        self.elements = elements
        self.position = position
        self.bgcolor = bgcolor
        self.padding = padding

    def draw(self, surface: pygame.Surface) -> List[MouseRegion]:
        """
        Draw the menu on the given pygame surface.
        """
        element_width = max([e.min_width for e in self.elements])
        width = element_width + 2 * self.padding
        total_height = sum([e.height for e in self.elements]) + (len(self.elements) + 1) * self.padding
        available_width = surface.get_width() - width
        available_height = surface.get_height() - total_height

        # TODO There might be a more elegant way to ensure the bit depth is sufficient
        bg_surface = pygame.Surface((width, total_height), pygame.SRCALPHA, depth=max(surface.get_bitsize(), 16))
        if self.bgcolor is not None:
            bg_surface.fill(self.bgcolor)

        regions = []
        element_y = 0
        for element in self.elements:
            rect = pygame.Rect(self.padding, element_y + self.padding, element_width, element.height)
            regions += element.draw(bg_surface.subsurface(rect))
            element_y += element.height + self.padding

        x = available_width * self.position[0]
        y = available_height * self.position[1]
        surface.blit(bg_surface, pygame.Rect(x, y, width, total_height))
        return [r.move(x, y) for r in regions]

    def handle_mouse_events(self, events: List[MouseEvent]):
        """
        This method needs to be called for received mouse events to enable interactive elements like buttons.
        """
        for event in events:
            for element in self.elements:
                element.handle_mouse_event(event)


class Label(GuiElement):
    """
    Label to be part of a `Menu`
    """

    def __init__(self, text: str, font: pygame.freetype.Font = None, size: int = 20, align: float = 0.5,
                 fgcolor: Tuple = DEFAULT_FGCOLOR, bgcolor: Tuple = None):
        """
        :param text: Label text (can be multi-line)
        :param font: Defaults to Bedstead if not set
        :param size: Font size
        :param align: Horizontal text position from 0 (left) to 1 (right)
        :param fgcolor: Foreground color as RGB or RGBA
        :param bgcolor: Background color as RGB or RGBA
        """
        self._size = size
        self._font = font if font else BEDSTEAD
        self._text = text
        self.align = align
        self.fgcolor = fgcolor
        self.bgcolor = bgcolor
        self._calculate_dimensions()

    @property
    def text(self):
        """"""
        return self._text

    @text.setter
    def text(self, value: str):
        self._text = value
        self._calculate_dimensions()

    def _calculate_dimensions(self):
        lines = self._text.splitlines()
        preview_rects = [self._font.get_rect(line, size=self._size) for line in lines]
        font_line_height = self._font.get_sized_height(self._size)
        self._extra = font_line_height * 0.2
        self._line_height = font_line_height + 2 * self._extra
        self._height = self._line_height * len(lines)
        self._width = max([r.width for r in preview_rects]) + 2 * self._extra

    @property
    def height(self) -> int:
        return self._height

    @property
    def min_width(self) -> int:
        return self._width

    def draw(self, surface: pygame.Surface) -> List[MouseRegion]:
        if self.bgcolor is not None:
            surface.fill(self.bgcolor)
        self._draw_text(surface)
        return []

    def _draw_text(self, surface: pygame.Surface):
        offset = (surface.get_width() - self._width) * self.align
        for i, line in enumerate(self._text.splitlines()):
            self._font.render_to(surface, (self._extra + offset, self._line_height * i + self._extra), line,
                                 size=self._size,
                                 fgcolor=self.fgcolor)


class Button(Label):
    """
    Button to be part of a `Menu`
    """
    __count = 0

    def __new__(cls, *args, **kwargs):
        __instance = super().__new__(cls)
        __instance._numeric_id = cls.__count
        cls.__count += 1
        return __instance

    def __init__(self, text: str, action: Callable,
                 font: pygame.freetype.Font = None, size: int = 20, align: float = 0.5,
                 fgcolor: Tuple = DEFAULT_FGCOLOR, bgcolor: Tuple = DEFAULT_BUTTON_BGCOLOR,
                 hlbgcolor: Tuple = DEFAULT_BUTTON_HLBGCOLOR):
        """
        :param text: Label text (can be multi-line)
        :param action: Click handler
        :param font: Defaults to Bedstead if not set
        :param size: Font size
        :param align: Horizontal text position from 0 (left) to 1 (right)
        :param fgcolor: Foreground color as RGB or RGBA
        :param bgcolor: Background color as RGB or RGBA
        :param hlbgcolor: Background color as RGB or RGBA when highlighted
        """
        super().__init__(text, font, size, align, fgcolor, bgcolor)
        self._action = action
        self._hlbgcolor = hlbgcolor
        self._pressed = False
        self._hover = False

    @property
    def region_name(self):
        return f'async2v.pygame.gui.button{self._numeric_id}'

    def draw(self, surface: pygame.Surface) -> List[MouseRegion]:
        if not self._hover and self.bgcolor is not None:
            surface.fill(self.bgcolor)
        elif self._hover and self._hlbgcolor is not None:
            surface.fill(self._hlbgcolor)
        super()._draw_text(surface)
        rect = surface.get_rect()  # type: pygame.Rect
        rect = rect.move(*surface.get_abs_offset())
        return [MouseRegion(self.region_name, rect, rect.size)]

    def handle_mouse_event(self, event: MouseEvent):
        if event.region.name == self.region_name:
            if event.button == MouseButton.LEFT and event.event_type == MouseEventType.DOWN:
                self._pressed = True
                return
            elif event.button == MouseButton.LEFT and event.event_type == MouseEventType.UP and self._pressed:
                self._action()
            elif event.event_type == MouseEventType.ENTER:
                self._hover = True
            elif event.event_type == MouseEventType.LEAVE:
                self._hover = False

        self._pressed = False


def render_hud_text(surface: pygame.Surface, text: str,
                    font: pygame.freetype.Font = None, size: int = 20,
                    fgcolor=DEFAULT_FGCOLOR, bgcolor=None, position: Tuple[float, float] = (0, 0)):
    """
    Draw text on the screen

    This is a shorthand for drawing a `Menu` with exactly one `Label` element.

    :param surface: Surface to draw text on
    :param text: Hud text (can be multi-line)
    :param font: Defaults to Bedstead if not set
    :param size: Font size
    :param fgcolor: Foreground color as RGB or RGBA
    :param bgcolor: Background color as RGB or RGBA
    :param position: Relative position within the display from (0, 0) to (1, 1). (0.5, 0.5) for center.
    """
    Menu([Label(text, font, size, fgcolor=fgcolor, bgcolor=bgcolor)], position=position).draw(surface)
