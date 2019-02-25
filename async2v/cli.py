"""
Build a command-line interface for your application.

Subclass `ApplicationLauncher` and override the required methods to configure your components and run your
application without having to write boilerplate.

This gives you the predefined commands :code:`run`, :code:`graph` and possibly additional commands provided by
component configurators. In addition, you can also define additional commands by subclassing `Command` and add them
to your application by registering a subclass of `Configurator`.
"""
import argparse
import argcomplete

import time
from typing import List, Dict

import logwood
import sys

from async2v.application import Application
# noinspection PyProtectedMember
from async2v.application._graph import ApplicationGraph
# noinspection PyProtectedMember
import async2v.application._graph


class Command:
    """
    Abstract base class to define subcommands for the command line interface

    .. automethod:: __call__
    """

    @property
    def name(self) -> str:
        """
        Name of the subcommand
        """
        raise NotImplementedError

    @property
    def help(self) -> str:
        """
        Help text used in the command line interface
        """
        raise NotImplementedError

    @property
    def needs_app(self) -> bool:
        """
        Return :code:`True` if your command requires a fully configured `Application` instance.
        """
        raise NotImplementedError

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """
        Override to register commandline arguments for this command

        :param parser:
        """
        raise NotImplementedError

    def __call__(self, args, app: Application = None) -> None:
        """
        Override to define the command logic.

        :param args: Arguments parsed by argparse
        :param app: Holds an `Application` instance if `needs_app` is :code:`True`, otherwise :code:`None`
        """
        raise NotImplementedError


class Configurator:
    """
    Abstract base class to define reusable command line arguments and configuration parsers

    A configurator can optionally provide one or more subcommands by returning a list of `Command` instances.
    """

    def add_app_arguments(self, parser: argparse.ArgumentParser) -> None:
        """
        Override to register additional parameters for the application.

        :param parser:
        """
        pass

    @property
    def commands(self) -> List[Command]:
        """
        Override to register additional subcommands.
        """
        return []


class _DefaultConfigurator(Configurator):

    def add_app_arguments(self, parser: argparse.ArgumentParser) -> None:
        pass

    @property
    def commands(self) -> List[Command]:
        return [self.RunCommand(), self.GraphCommand()]

    class RunCommand(Command):
        name = 'run'
        help = 'Run the application'
        needs_app = True

        def add_arguments(self, parser: argparse.ArgumentParser):
            pass

        def __call__(self, args, app: Application = None):
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

        def add_arguments(self, parser: argparse.ArgumentParser):
            group = parser.add_argument_group('Graph')
            group.add_argument('--source', help='Print dot code instead of creating graph', action='store_true')
            group.add_argument('-o', '--output', metavar='FILENAME', default='graph',
                               help='Dot source output filename. '
                                    'The source will be rendered to FILENAME.EXT according to output format.')
            # noinspection PyProtectedMember
            group.add_argument('-f', '--format', metavar='FORMAT', default='pdf',
                               choices=async2v.application._graph.get_formats(),
                               help='Output format')

        def __call__(self, args, app: Application = None):
            graph = ApplicationGraph(app._registry)
            if args.source:
                print(graph.source())
            else:
                graph.draw(args.output, args.format)


class ApplicationLauncher:
    """
    Main entry point for a async2v commandline application.

    * To register components, override `register_application_components` and call :code:`app.register(...)`.
    * Some components have predefined configurators that can be hooked into the launcher:

      * Override :code:`__init__` and call :code:`self.add_configurator(...)` to register them.
      * Construct the configuration with :code:`MyConfigurator.config_from_args(...)` in
        `register_application_components`.

    * Override `add_app_arguments` to register argparse arguments for your application.
    """

    def __init__(self):
        self._configurators = [_DefaultConfigurator()]  # type: List[Configurator]
        self._commands = {}  # type: Dict[str, Command]
        self.parser = argparse.ArgumentParser()
        self.parser.add_argument('-v', '--verbose', action='count', default=0)
        self.parser.add_argument('-q', '--quiet', action='count', default=0)

        # noinspection PyProtectedMember
        self.subparsers: argparse._SubParsersAction = self.parser.add_subparsers(help='command', dest='command')

    def add_configurator(self, configurator: Configurator):
        """
        Add a configurator to be evaluated by argparse.

        This method needs to be called from the constructor to be effective.

        :param configurator: Configurator provided by a configurable `Component`
        """
        self._configurators.append(configurator)

    def add_app_arguments(self, parser: argparse.ArgumentParser):
        """
        Override this method to specify arguments that are needed to construct the application, i.e. when
        `register_application_components` is called.

        :param parser:
        """
        pass

    def register_application_components(self, args, app: Application):
        """
        This method must be overridden.

        Use :code:`app.register(...)` to register your components, using the parsed commandline args.

        :param args: Arguments parsed by argparse
        :param app:
        """
        raise NotImplementedError

    def main(self, args=None):
        """
        Launch the commandline interface.

        :param args: Optionally pass arguments. If not given, the arguments passed to the program will be parsed.
        """
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
        for configurator in self._configurators:
            configurator.add_app_arguments(parser)

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
