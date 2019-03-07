Keyboard
========

This chapter of the tutorial introduces keyboard handling.

We start with the result of the `second chapter <../tutorial/02_synchronous_filter>`, the simple app with the flip filter.

The code examples included in this chapter are available as ready-to-run examples under ``examples/tutorial/04_*.py``.


Add a keyboard handler
----------------------

Override the class `EventBasedKeyboardHandler` and define the keyboard actions by adding them to the class variable
``ACTIONS``. An `Action` needs a name, optionally it can have default keys and a description.

A keyboard handler is configured similarly to other components. It is vital to call ``layout_from_args`` on the
configurator of your keyboard layout subclass (and not on the generic `EventBasedKeyboardHandler`),
as it needs the ``ACTIONS`` field of that subclass to generate the layout.

Finally, pass a configured instance of the keyboard handler to the constructor of your `MainWindow`.

.. literalinclude:: ../../examples/tutorial/04_01.py
  :language: python
  :emphasize-lines: 30-34,43,50,52

When running the example, the new keyboard actions are visible in the on-screen help (``F1``), but they don't trigger
any behavior yet.


Use keyboard action events
--------------------------

Any `EventBasedKeyboardHandler` pushes keyboard events containing `KeyboardEvent` payload to the `KEYBOARD_EVENT` key.
To process them, add a suitable input field. Use a `Buffer` to process every event.

.. literalinclude:: ../../examples/tutorial/04_02.py
  :language: python
  :emphasize-lines: 20,24-25,28-38

Now, the cursor keys toggle horizontal & vertical flipping.


Define a custom keyboard layout
-------------------------------

The builtin keyboard configurator allows to override the default key bindings given in the `Action`.
To do so, first generate a keyboard layout file:

::

    ./keyboard.py create-keyboard-layout

This generates an file ``keyboard.conf``, which is pre-filled with the defaults:

::

    toggle_horizontal_flip  LEFT RIGHT
    toggle_vertical_flip    UP DOWN

Modify this file to override the key bindings:

::

    toggle_horizontal_flip  a s
    toggle_vertical_flip    w d

When running the application again the new keybindings are in effect, as ``keyboard.conf`` is read and applied
automatically if present. You may also use the option ``--keyboard-layout`` to specify a different file on startup.


See the `keyboard` module and the examples (especially ``text_based_*.py``) for more keyboard-related features.
