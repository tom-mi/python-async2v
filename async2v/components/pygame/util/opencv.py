import cv2
import pygame

from async2v.components.opencv.video import Frame


def opencv_to_pygame(frame: Frame) -> pygame.Surface:
    conversion = cv2.COLOR_GRAY2RGB if frame.channels == 1 else cv2.COLOR_BGR2RGB
    return pygame.surfarray.make_surface(cv2.transpose(cv2.cvtColor(frame.image, conversion)))
