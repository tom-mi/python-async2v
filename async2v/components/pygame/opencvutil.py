import cv2
import pygame

from async2v.components.opencv.video import Frame


def opencv_to_pygame(frame: Frame) -> pygame.Surface:
    return pygame.surfarray.make_surface(cv2.transpose(cv2.cvtColor(frame.image, cv2.COLOR_BGR2RGB)))
