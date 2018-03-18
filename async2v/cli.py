import argparse
import argcomplete

import time
from typing import List, Dict

import logwood
import sys

from async2v.application import Application
from async2v.application.graph import ApplicationGraph
import async2v.application.graph


class Command:

    @property
    def name(self) -> str:
        raise NotImplementedError

    @property
    def help(self) -> str:
        raise NotImplementedError

    @property
    def needs_app(self) -> bool:
        raise NotImplementedError

    @staticmethod
    def add_arguments(parser: argparse.ArgumentParser):
        raise NotImplementedError

    @staticmethod
    def __call__(args, app: Application = None):
        raise NotImplementedError


class Configurator:

    def add_app_arguments(self, parser: argparse.ArgumentParser) -> None:
        raise NotImplementedError

    @property
    def commands(self) -> List[Command]:
        raise NotImplementedError


class DefaultConfigurator(Configurator):

    def add_app_arguments(self, parser: argparse.ArgumentParser) -> None:
        pass

    @property
    def commands(self) -> List[Command]:
        return [self.RunCommand(), self.GraphCommand()]

    class RunCommand(Command):
        name = 'run'
        help = 'Run the application'
        needs_app = True

        @staticmethod
        def add_arguments(parser: argparse.ArgumentParser):
            pass

        @staticmethod
        def __call__(args, app: Application = None):
            app.start()
            while app.is_alive():
                try:
                    time.sleep(0.1)
                except KeyboardInterrupt:
                    break
            app.stop()

    class GraphCommand(Command):
        name = 'graph'
        help = 'Draw an application graph using graphviz'
        needs_app = True

        @staticmethod
        def add_arguments(parser: argparse.ArgumentParser):
            group = parser.add_argument_group('Graph')
            group.add_argument('--source', help='Print dot code instead of creating graph', action='store_true')
            group.add_argument('-o', '--output', metavar='FILENAME', default='graph',
                               help='Dot source output filename. '
                                    'The source will be rendered to FILENAME.EXT according to output format.')
            group.add_argument('-f', '--format', metavar='FORMAT', default='pdf',
                               choices=async2v.application.graph.get_formats(),
                               help='Output format')

        @staticmethod
        def __call__(args, app: Application = None):
            graph = ApplicationGraph(app._registry)
            if args.source:
                print(graph.source())
            else:
                graph.draw(args.output, args.format)


class ApplicationLauncher:

    def __init__(self):
        self._configurators = [DefaultConfigurator()]  # type: List[Configurator]
        self._commands = {}  # type: Dict[str, Command]
        self.parser = argparse.ArgumentParser()
        self.parser.add_argument('-v', '--verbose', action='count', default=0)
        self.parser.add_argument('-q', '--quiet', action='count', default=0)

        self.subparsers = self.parser.add_subparsers(help='command', dest='command')  # type: argparse._SubParsersAction

    def add_configurator(self, configurator: Configurator):
        self._configurators.append(configurator)

    def add_app_arguments(self, parser: argparse.ArgumentParser):
        raise NotImplementedError

    def register_application_components(self, args, app: Application):
        raise NotImplementedError

    def main(self, args=None):
        self._configure_parser()
        argcomplete.autocomplete(self.parser)
        args = self.parser.parse_args(args)
        logwood.basic_config(
            format='%(timestamp).6f %(level)-5s %(name)s: %(message)s',
            level=self._get_loglevel(args),
        )

        if not args.command:
            self.parser.print_usage()
            sys.exit(1)
        else:
            command = self._commands[args.command]
            if command.needs_app:
                app = Application()
                self.register_application_components(args, app)
                command.__call__(args, app)
            else:
                command.__call__(args)

    def _configure_parser(self):
        for launcher in self._configurators:
            for command in launcher.commands:
                cmd_parser = self.subparsers.add_parser(command.name,
                                                        help=command.help)  # type: argparse.ArgumentParser
                command.add_arguments(cmd_parser)
                if command.needs_app:
                    self._add_all_app_args(cmd_parser)
                self._commands[command.name] = command

    def _add_all_app_args(self, parser: argparse.ArgumentParser):
        self.add_app_arguments(parser)
        for launcher in self._configurators:
            launcher.add_app_arguments(parser)

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
