from async2v.components.pygame.display import OpenCvDebugDisplay
from async2v.components.pygame.main import MainWindow


def test_simple_application(app, video_source):
    displays = [OpenCvDebugDisplay()]
    main_window = MainWindow(displays=displays)
    app.register(video_source, main_window)
    app.start()
    app.join(20)

    assert not app.is_alive()
    assert not app.has_error_occurred()
