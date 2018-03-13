import argparse

import time

import logwood
import sys

from async2v.application import Application


class ApplicationLauncher:

    def __init__(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('-v', '--verbose', action='store_true')

        self.setup_application_arguments(parser)
        subparsers = parser.add_subparsers(help='command', dest='command')

        run_parser = subparsers.add_parser('run')

        self._parser = parser

    def setup_application_arguments(self, parser: argparse.ArgumentParser):
        raise NotImplementedError

    def __call__(self):
        args = self._parser.parse_args()
        logwood.basic_config(
            format='%(timestamp)s %(level)-5s %(name)s: %(message)s',
            level=logwood.DEBUG if args.verbose else logwood.INFO,
        )
        if not args.command:
            self._parser.print_usage()
            sys.exit(1)

        app = Application()
        self.register_application_components(args, app)

        if args.command == 'run':
            app.start()
            while app.is_alive():
                try:
                    time.sleep(0.1)
                except KeyboardInterrupt:
                    break
            app.stop()

    def register_application_components(self, args, app: Application):
        raise NotImplementedError
