#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK

from async2v.application import Application
from async2v.cli import ApplicationLauncher
from async2v.components.opencv.video import VideoSource, SimpleDisplaySink


class Launcher(ApplicationLauncher):

    def __init__(self):
        super().__init__()
        self.add_configurator(VideoSource.configurator())

    def register_application_components(self, args, app: Application):
        source = VideoSource(VideoSource.configurator().config_from_args(args))
        sink = SimpleDisplaySink('source')
        app.register(source, sink)


def main():
    launcher = Launcher()
    launcher.main()


if __name__ == '__main__':
    main()
