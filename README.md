# python-async2v

Framework for rapid prototyping of computer-vision software.

It is based on [asyncio](https://docs.python.org/3/library/asyncio.html).
To get the most out of it, [pygame](https://www.pygame.org/news) and [OpenCV](https://opencv.org/) are required.

*Write less boilerplate, instead focus on the interesting things.*

## Idea

### Event-driven, asynchronous components

Live video processing usually involves inputs coming with a more or less fixed frame rate, processing steps that might
take anything from milliseconds to seconds and various ways to merge and display the results.

For this, a blocking pipeline doing one step after the other (like the infinite while-loop most OpenCV projects start
with) is not suitable: It will always be as fast as its slowest part, with additional penalty for performance-hungry steps.
Also, branching and merging is not trivial.

The async2v framework has a different approach: The application is composed of loosely coupled components, communicating
solely with events.
The events leave and enter the components through defined inputs & outputs, which connect the components in a
fixed, understandable way to a directed graph.

### Modeling unpredictable input and output

Components are triggered either by a timer or by incoming events. Either way there is usually no way to predict how
many events have arrived at the various inputs during the last processing step (except for very simple components).
This fact is taken into account by providing inputs that allow to handle asynchronous input events in a convenient way:

* A `Latest` input field will only retain the last received event.
* A `Buffer` input field collects all input since the last processing step and is cleared after each processing step.
* A `History` input field retains up to a fixed number of events, but is not cleared between processing steps.
* New events can be pushed to `Output` fields during processing steps once, multiple times or not at all.

### Threading

While the framework makes heavy use of asyncio (and a little threading) to propagate the events to the components &
and call the processing methods at the right time, the processing logic in the components could be completely synchronous.

However, for performance reasons it is usually necessary to offload expensive calculations or blocking I/O to separate threads.
Thanks to asyncio's `await`, this can be achieved using a one-liner that allows to synchronously wait for the result
of the calculation within the component itself, while not blocking other components at the same time.

### Sources, Filters & Sinks

Regarding inputs & outputs, there are 3 kinds of components:

* Sources only have outputs, such as a `VideoSource`
* Sinks only have inputs, such as a `SimpleDisplaySink`
* Filters have inputs and outputs. They usually contain the interesting processing logic.

### Iterating vs EventDriven

In async2v, components are either iterating (running at a fixed frame rate) ore event driven (one or more input fields
trigger processing on new events).
For special cases, there is also the possibility to subclass `BareComponent` to define custom processing behavior.

### Minimize Boilerplate

The async2v framework comes with a set of generic components that can be used in most projects, e.g. a video source or
a debug display. Some of the components come with `argparse` integration that allow to provide common settings like
resolution or source camera on the command line.

There is also support for building simple user interfaces, including text overlay, simple mouse & keyboard input (with
custom keyboard layout configuration), on-screen help, fullscreen mode and more.
