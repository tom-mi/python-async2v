#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK

from async2v.application import Application
from async2v.cli import ApplicationLauncher
from async2v.components.pygame.display import OpenCvDebugDisplay
from async2v.components.pygame.main import MainWindow


class Launcher(ApplicationLauncher):

    def __init__(self):
        super().__init__()
        self.add_configurator(MainWindow.configurator())

    def register_application_components(self, args, app: Application):
        displays = [
            OpenCvDebugDisplay()
        ]
        app.register(MainWindow(displays, config=MainWindow.configurator().config_from_args(args)))


def main():
    Launcher().main()


if __name__ == '__main__':
    main()
