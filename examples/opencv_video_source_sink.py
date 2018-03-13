#!/usr/bin/env python3
import argparse
import time

import logwood

from async2v.application import Application
from async2v.cli import ApplicationLauncher
from async2v.components.opencv.video import VideoSource, SimpleDisplaySink


class Launcher(ApplicationLauncher):

    def setup_application_arguments(self, parser: argparse.ArgumentParser):
        pass

    def register_application_components(self, args, app: Application):
        source = VideoSource()
        sink = SimpleDisplaySink('source')
        app.register(source, sink)


def main():
    launcher = Launcher()
    launcher()


if __name__ == '__main__':
    main()
