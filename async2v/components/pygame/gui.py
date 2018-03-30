"""
Very simple and basic gui elements.

Gui elements have a fixed height and a minimal width. They can only be aligned in vertical stacked groups.
Afterwards, all elements are drawn with the same width, which is the width of the widest element.
"""
from typing import List, Tuple, Callable

import pygame.freetype

from async2v.components.pygame.fonts import BEDSTEAD
from async2v.components.pygame.mouse import MouseRegion, MouseEvent, MouseButton, MouseEventType


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

    def __init__(self, elements: List[GuiElement], position: Tuple[float, float] = (0, 0), bgcolor=(0, 0, 0, 128),
                 padding: float = 4):
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

        bg_surface = pygame.Surface((width, total_height), pygame.SRCALPHA)
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

    def handle_mouse_event(self, event: MouseEvent):
        """
        This method needs to be called for each received mouse event to enable interactive elements like buttons.
        """
        for element in self.elements:
            element.handle_mouse_event(event)


class Label(GuiElement):
    def __init__(self, text: str, font: pygame.freetype.Font = BEDSTEAD, size: int = 20, align: float = 0.5,
                 fgcolor: Tuple = (255, 255, 255), bgcolor: Tuple = None):
        self._size = size
        self._font = font
        self._text = text
        self.align = align
        self.fgcolor = fgcolor
        self.bgcolor = bgcolor
        self._calculate_dimensions()

    @property
    def text(self):
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
    __count = 0

    def __new__(cls, *args, **kwargs):
        __instance = super().__new__(cls)
        __instance._numeric_id = cls.__count
        cls.__count += 1
        return __instance

    def __init__(self, text: str, action: Callable,
                 font: pygame.freetype.Font = BEDSTEAD, size: int = 20, align: float = 0.5,
                 fgcolor: Tuple = (255, 255, 255), bgcolor: Tuple = (64, 64, 64, 128),
                 hlbgcolor: Tuple = (128, 128, 128, 224)):
        super().__init__(text, font, size, align, fgcolor, bgcolor)
        self._action = action
        self.hlbgcolor = hlbgcolor
        self._pressed = False
        self._hover = False

    @property
    def region_name(self):
        return f'async2v.pygame.gui.button{self._numeric_id}'

    def draw(self, surface: pygame.Surface) -> List[MouseRegion]:
        if not self._hover and self.bgcolor is not None:
            surface.fill(self.bgcolor)
        elif self._hover and self.hlbgcolor is not None:
            surface.fill(self.hlbgcolor)
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
                    font: pygame.freetype.Font = BEDSTEAD, size: int = 20,
                    fgcolor=None, bgcolor=None, position: Tuple[float, float] = (0, 0)):
    Menu([Label(text, font, size, fgcolor=fgcolor, bgcolor=bgcolor)], position=position).draw(surface)
