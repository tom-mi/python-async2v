import pytest

from async2v.components.pygame import util


@pytest.mark.parametrize('src_resolution,target_resolution,expected', [
    ((400, 300), (400, 300), ((0, 0), (400, 300))),
    ((400, 300), (800, 600), ((0, 0), (800, 600))),
    ((400, 300), (1024, 600), ((112, 0), (800, 600))),
    ((400, 300), (800, 768), ((0, 84), (800, 600))),
    ((100, 300), (200, 200), ((67, 0), (66, 200))),
])
def test_scale_preserving_aspect(src_resolution, target_resolution, expected):
    assert util.scale_and_center_preserving_aspect(src_resolution, target_resolution) == expected


@pytest.mark.parametrize('number_of_screens, expected_layouts', [
    (1, [(1, 1)]),
    (2, [(1, 2), (2, 1)]),
    (3, [(1, 3), (2, 2), (3, 1)]),
    (4, [(1, 4), (2, 2), (4, 1)]),
    (5, [(1, 5), (2, 3), (3, 2), (5, 1)]),
    (11, [(1, 11), (2, 6), (3, 4), (4, 3), (6, 2), (11, 1)]),
])
def test_possible_screen_layouts(number_of_screens, expected_layouts):
    assert util.possible_screen_layouts(number_of_screens) == expected_layouts


@pytest.mark.parametrize('frames, screen_size, expected', [
    ([(100, 100)], (100, 100), (1, 1)),
    ([(100, 200)], (100, 100), (1, 1)),
    ([(100, 100), (100, 100)], (100, 200), (1, 2)),
    ([(100, 50), (300, 200), (300, 200)], (200, 200), (2, 2)),
    ([(100, 50), (300, 100), (300, 150)], (200, 200), (1, 3)),
])
def test_best_regular_screen_layout(frames, screen_size, expected):
    assert util.best_regular_screen_layout(frames, screen_size) == expected
