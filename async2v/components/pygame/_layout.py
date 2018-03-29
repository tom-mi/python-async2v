from typing import Tuple, List


def best_regular_screen_layout(src_frames: List[Tuple[int, int]], target: Tuple[int, int]) -> Tuple[int, int]:
    possible_layouts = possible_screen_layouts(len(src_frames))
    best_layout = None
    best_loss = None
    for layout in possible_layouts:
        loss = 0
        sub_frame_ratio = ((target[0] / layout[0]) / (target[1] / layout[1]))
        for frame in src_frames:
            ratio = frame[0] / frame[1]
            loss += abs(ratio - sub_frame_ratio)

        if best_loss is None or loss < best_loss:
            best_layout = layout
            best_loss = loss
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
