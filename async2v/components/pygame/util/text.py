from typing import Tuple

import pygame.freetype

from async2v.components.pygame.fonts import BEDSTEAD


def render_hud_text(surface: pygame.Surface, text: str,
                    font: pygame.freetype.Font = BEDSTEAD, size: int = 20,
                    fgcolor=None, bgcolor=None, position: Tuple[float, float] = (0, 0)):
    if not text:
        return
    lines = text.splitlines()
    preview_rects = [font.get_rect(line, size=size) for line in lines]
    font_line_height = font.get_sized_height(size)
    extra = font_line_height * 0.1
    line_height = font_line_height + 2 * extra
    height = line_height * len(lines)
    width = max([r.width for r in preview_rects]) + 2 * extra

    available_width = surface.get_width() - width
    available_height = surface.get_height() - height

    x = available_width * position[0]
    y = available_height * position[1]

    if bgcolor is not None:
        bg_surface = pygame.Surface((width, height), pygame.SRCALPHA)
        bg_surface.fill(bgcolor)
        surface.blit(bg_surface, pygame.Rect(x, y, width, height))

    for i, line in enumerate(lines):
        font.render_to(surface, (x + extra, y + line_height * i + extra), line, size=size, fgcolor=fgcolor)
