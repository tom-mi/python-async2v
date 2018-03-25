import queue

import pygame

from async2v.components.pygame.mouse import EventBasedMouseHandler, MouseRegion, MouseEvent, MouseEventType, \
    MouseButton, MouseMovement


def test_event_based_mouse_handler():
    event_queue = queue.Queue()
    movement_queue = queue.Queue()
    handler = EventBasedMouseHandler()
    handler.event.set_queue(event_queue)
    handler.movement.set_queue(movement_queue)
    main_region = MouseRegion('main', pygame.Rect(0, 0, 30, 20), (30, 20))
    foo_region = MouseRegion('foo', pygame.Rect(10, 12, 5, 8), (24, 58))

    handler.push_regions([main_region, foo_region])
    handler.push_button_down((5, 5), 1)
    handler.push_button_up((5, 5), 1)

    assert event_queue.get_nowait().value == MouseEvent(main_region, (5, 5), MouseEventType.ENTER)
    assert event_queue.get_nowait().value == MouseEvent(main_region, (5, 5), MouseEventType.DOWN,
                                                        button=MouseButton.LEFT)
    assert event_queue.get_nowait().value == MouseEvent(main_region, (5, 5), MouseEventType.UP, button=MouseButton.LEFT)

    assert event_queue.qsize() == 0
    assert movement_queue.qsize() == 0

    handler.push_movement((12, 15), (7, 10), (0, 1, 0))
    handler.push_regions([main_region])

    assert event_queue.get_nowait().value == MouseEvent(main_region, (12, 15), MouseEventType.LEAVE)
    assert event_queue.get_nowait().value == MouseEvent(foo_region, (12, 15), MouseEventType.ENTER)
    assert movement_queue.get_nowait().value == MouseMovement(foo_region, (12, 15), (7, 10),
                                                              {MouseButton.LEFT: False, MouseButton.MIDDLE: True,
                                                               MouseButton.RIGHT: False})
    assert event_queue.get_nowait().value == MouseEvent(foo_region, (12, 15), MouseEventType.LEAVE)
    assert event_queue.get_nowait().value == MouseEvent(main_region, (12, 15), MouseEventType.ENTER)

    assert event_queue.qsize() == 0
    assert movement_queue.qsize() == 0
