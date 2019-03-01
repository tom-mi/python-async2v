#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK
from async2v.application import Application
from async2v.cli import ApplicationLauncher


class Launcher(ApplicationLauncher):

    def register_application_components(self, args, app: Application):
        pass


def main():
    Launcher().main()


if __name__ == '__main__':
    main()
