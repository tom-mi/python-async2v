Tutorial - Getting Started
==========================

This chapter of the tutorial guides you to creating your first application that displays a video stream from
a connected webcam.

Install async2v
---------------

To use async2v as it is intended, install it with `pygame <https://www.pygame.org/>`_
and `OpenCV <https://opencv.org/>`_ support:

::

    pip install async2v[pygame,opencv]

Create an empty application
---------------------------

The following code contains a minimal, although not very useful application:

.. literalinclude:: ../../examples/tutorial/01_01.py
  :language: python

The entry point of every application is an application-specific subclass of the `ApplicationLauncher` class.
To launch the application, call the method `main <ApplicationLauncher.main>` on an instance of the custom launcher class.
Within the custom launcher, you must override the method `register_application_components`.
It is a callback that is called during initialization of the application.
In this example it is empty, giving us an empty application with no components.

Still, we can run our application:

::

    ./getting_started.py run

Nothing seems to happen, as there are no components being started. Stop the application by pressing ``CTRL+C``.

Note also the second line ``# PYTHON_ARGCOMPLETE_OK``. In combination with the ``argcomplete`` package, it
allows to get bash completion for your application.
See `the documentation of argcomplete <https://pypi.org/project/argcomplete/>`_ for how to activate global completion.


Add a display
-------------

The builtin pygame-based `OpenCvDebugDisplay` is a good starting point, as it does not need any configuration and can display
data from multiple sources simultaneously.

Pygame-based displays are embedded in a `MainWindow` component, which is the central application window.
A `MainWindow` can have one or more displays.

.. literalinclude:: ../../examples/tutorial/01_02.py
  :language: python
  :emphasize-lines: 13-17

All components must be instantiated and registered on the `Application` instance passed to the
`register_application_components` method.

When you start the app now, an empty window is shown. Press ``F1`` for an on-screen help.

Exit the application with ``ESCAPE`` from the window or by pressing ``CTRL+C`` in the terminal running the application.


Configure the main window
-------------------------

Some of the builtin components can be configured, for example it is possible to specify a resolution or enable
fullscreen mode for the `MainWindow`. This can be done programmatically, but usually you want to switch things like that
on the fly from the commandline. To save you from writing argparse options for that, there is builtin argparse support
for all many components that come with async2v:

* Before parsing the commandline arguments, additional options are registered with the application's argparse parser.
  The right place for that is the constructor of the application launcher.
* When instantiating and registering the components, the component-specific configuration is extracted from the parsed
  argparse args. This is done in the already known `register_application_components` method.

While it is possible to directly use the application's `ArgumentParser <argparse.ArgumentParser>`,
there is also a reusable mechanism built into async2v.
Both registering the arguments and constructing the component configuration from the args can be encapsulated in
`Configurator` classes.


.. literalinclude:: ../../examples/tutorial/01_03.py
  :language: python
  :emphasize-lines: 12-14,20

For configurable components built into async2v, there is the following convention:

* The static method ``component.configurator()`` returns an instance of a configurator for that component.
* The method ``configurator.config_from_args(args)`` takes the parsed argparse args and returns a configuration
  that can be used to construct a configured instance of the component.

Try out the new options and commands added by the configurator, for example:

::

    ./getting_started.py run --resolution 500x500
    ./getting_started.py list-resolutions
    ./getting_started.py run --fullscreen --resolution 640x480
