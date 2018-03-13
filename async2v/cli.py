import argparse

import time

import logwood
import sys

from async2v.application import Application
from async2v.graph import draw_application_graph


class ApplicationLauncher:

    def __init__(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('-v', '--verbose', action='count', default=0)
        parser.add_argument('-q', '--quiet', action='count', default=0)

        self.setup_application_arguments(parser)
        subparsers = parser.add_subparsers(help='command', dest='command')

        run_parser = subparsers.add_parser('run')

        graph_parser = subparsers.add_parser('graph')

        self._parser = parser

    def setup_application_arguments(self, parser: argparse.ArgumentParser):
        raise NotImplementedError

    def __call__(self):
        args = self._parser.parse_args()
        logwood.basic_config(
            format='%(timestamp).6f %(level)-5s %(name)s: %(message)s',
            level=self._get_loglevel(args),
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
        elif args.command == 'graph':
            draw_application_graph(app.graph)

    @staticmethod
    def _get_loglevel(args):
        verbosity = args.verbose - args.quiet
        if verbosity <= -3:
            return logwood.CRITICAL
        elif verbosity == -2:
            return logwood.ERROR
        elif verbosity == -1:
            return logwood.WARNING
        elif verbosity == 0:
            return logwood.INFO
        else:
            return logwood.DEBUG

    def register_application_components(self, args, app: Application):
        raise NotImplementedError
