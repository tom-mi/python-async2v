import os.path
import subprocess

import pytest

example_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'examples'))
video_file = os.path.abspath(os.path.join(os.path.dirname(__file__), 'data', 'video.mp4'))


@pytest.mark.parametrize('command', [
    [os.path.join(example_dir, 'terminator_vision.py'), 'run', '--source-file', video_file],
    [os.path.join(example_dir, 'person_tracking.py'), 'run', '--source-file', video_file],
    [os.path.join(example_dir, 'opencv_video_source_sink.py'), 'run', '--source-file', video_file],
])
def test_command(command):
    subprocess.check_call(command)
