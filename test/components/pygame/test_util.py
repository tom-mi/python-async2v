import pytest

from async2v.components.pygame.util import scale_and_center_preserving_aspect


@pytest.mark.parametrize('src_resolution,target_resolution,expected', [
    ((400, 300), (400, 300), ((0, 0), (400, 300))),
    ((400, 300), (800, 600), ((0, 0), (800, 600))),
    ((400, 300), (1024, 600), ((112, 0), (800, 600))),
    ((400, 300), (800, 768), ((0, 84), (800, 600))),
    ((100, 300), (200, 200), ((67, 0), (66, 200))),
])
def test_scale_preserving_aspect(src_resolution, target_resolution, expected):
    assert scale_and_center_preserving_aspect(src_resolution, target_resolution) == expected
