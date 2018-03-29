from typing import Tuple, List


def scale_and_center_preserving_aspect(src_resolution: Tuple[int, int],
                                       target_resolution: Tuple[int, int]) -> Tuple[Tuple[int, int], Tuple[int, int]]:
    width = min(target_resolution[0], int(target_resolution[1] / src_resolution[1] * src_resolution[0]))
    height = min(target_resolution[1], int(target_resolution[0] / src_resolution[0] * src_resolution[1]))
    offset_x = int((target_resolution[0] - width) / 2)
    offset_y = int((target_resolution[1] - height) / 2)
    return (offset_x, offset_y), (width, height)


def best_regular_screen_layout(src_frames: List[Tuple[int, int]], target: Tuple[int, int]) -> Tuple[int, int]:
    possible_layouts = possible_screen_layouts(len(src_frames))
    best_layout = None
    best_ratio = 0
    for layout in possible_layouts:
        sub_frame_target = (int(target[0] / layout[0]), int(target[1] / layout[1]))
        screen_coverage = 0
        for frame in src_frames:
            _, resized = scale_and_center_preserving_aspect(frame, sub_frame_target)
            screen_coverage += resized[0] * resized[1]

        ratio = screen_coverage / (target[0] * target[1])
        if ratio > best_ratio:
            best_layout = layout
            best_ratio = ratio
    return best_layout


def possible_screen_layouts(number_of_frames: int) -> List[Tuple[int, int]]:
    possible_layouts = []
    best_n_y = number_of_frames + 1
    for n_x in range(1, number_of_frames + 1):
        for n_y in range(1, best_n_y):
            if n_x * n_y >= number_of_frames:
                best_n_y = n_y
                possible_layouts.append((n_x, n_y))
                break

    return possible_layouts
