from threading import Event
from time import sleep

import PIL

from helpers import setup_logger
from ui.utils import to_be_foreground

logger = setup_logger(__name__, "info")


class BaseUIElement(object):

    def __init__(self, i, o, name, override_left=True, input_necessary=True):
        """
        Sets the most basic variables and checks whether the input object
        is supplied in case it's necessary. To be called by a child object.
        """
        self.i = i
        self.o = o
        self.name = name
        self._in_foreground = Event()
        self._in_background = Event()
        self._input_necessary = input_necessary
        self._override_left = override_left
        if not i and input_necessary:
            raise ValueError("UI element {} needs an input object supplied!")

    @property
    def in_foreground(self):
        return self._in_foreground.isSet()

    @in_foreground.setter
    def in_foreground(self, value):
        self._in_foreground.set() if value else self._in_foreground.clear()

    @property
    def in_background(self):
        return self._in_background.isSet()

    @in_background.setter
    def in_background(self, value):
        self._in_background.set() if value else self._in_background.clear()

    def to_foreground(self):
        """
        A method that is called once in ``activate`` to set all the variables,
        activates the input device and draw the first image on the display.
        """
        logger.debug("{} in foreground".format(self.name))
        self.in_background = True
        self.in_foreground = True
        self.activate_input()
        self.refresh()

    def to_background(self):
        """ Signals ``activate`` to finish executing. """
        self.in_foreground = False
        logger.debug("refresher {} in background".format(self.name))

    def activate(self):
        """
        A method which is called when the UI element needs to start operating.
        Is blocking, sets up input&output devices, refreshes the UI element,
        then calls the ``idle_loop`` method while the UI element is active.
        ``self.in_foreground`` is True, while callbacks are executed from the
        input device thread.
        """
        logger.debug("{} activated".format(self.name))
        self.to_foreground()
        while self.is_active:
            self.idle_loop()
        logger.debug(self.name+" exited")
        return True

    def is_active(self):
        """
        A condition to be checked by ``activate`` to see when the UI element
        is active. Can be overridden by child elements if necessary.
        """
        return self.in_background

    def idle_loop(self):
        """
        A method that will be called all the time while the UI element is in background
        (regardless of whether it's in foreground or not).
        To be implemented by a child object.
        """
        raise NotImplementedError

    def deactivate(self):
        """ Deactivates the UI element, exiting it."""
        self.in_foreground = False
        self.in_background = False
        logger.debug("{} deactivated".format(self.name))

    def print_name(self):
        """ A debug method. Useful for hooking up to an input event so that
        you can see which UI element is currently active. """
        logger.debug("{} is currently active".format(self.name))

    def print_keymap(self):
        """ A debug method. Useful for hooking up to an input event so that
        you can see what's the keymap of a currently active UI element. """
        logger.debug("{} has keymap: {}".format(self.name, self.keymap))

    def process_callback(self, func):
        """
        Decorates a function so that during its execution the UI element stops
        being in foreground. Is typically used as a wrapper for a callback from
        input event processing thread. After callback's execution is finished,
        sets the keymap again and refreshes the refresher.
        """
        def wrapper(*args, **kwargs):
            self.to_background()
            func(*args, **kwargs)
            logger.debug("{}: executed wrapped function: {}".format(self.name, func.__name__))
            if self.in_background:
                self.to_foreground()
        wrapper.__name__ == func.__name__
        return wrapper

    def process_keymap(self, keymap):
        """
        Processes the keymap, wrapping all callbacks using the ``process_callback`` method.
        If a string is supplied instead of a callable, it looks it up from methods -
        if a method is not found, raises ``ValueError``.
        Also, sets KEY_LEFT to ``deactivate`` unless ``override_left``
        keyword argument is False (override with caution).
        """
        logger.debug("{}: processing keymap - {}".format(self.name, keymap))
        for key in keymap:
            callback_or_name = self.process_callback(keymap[key])
            if isinstance(callback_or_name, basestring):
                if hasattr(self, callback_or_name):
                    callback_or_name = getattr(self, callback_or_name)
                else:
                    raise ValueError("{}: {} not an attribute/method".format(self.name, callback_or_name))
            if callable(callback_or_name):
                keymap[key] = callback_or_name
            else:
                raise ValueError("{}: {} is not a callable".format(self.name, callback_or_name))
        if self._override_left:
            if not "KEY_LEFT" in keymap:
                keymap["KEY_LEFT"] = self.deactivate
        return keymap

    def set_keymap(self, keymap):
        """
        Receives and processes UI element's keymap (filtered using ``process_keymap``
        before setting).
        """
        self.keymap = self.process_keymap(keymap)

    def update_keymap(self, new_keymap):
        """Sets the refresher's keymap (filtered using ``process_keymap`` before setting)."""
        self._override_left = False
        processed_keymap = self.process_keymap(new_keymap)
        self._override_left = True
        self.keymap.update(processed_keymap)

    def configure_input(self):
        """
        Configures the input device - you can set your keymap, streaming callbacks
        or both - abstracting away ``stop_listen`` and ``listen``. Can be overridden
        by child elements.
        """
        self.i.clear_keymap()
        self.i.set_keymap(self.keymap)

    @to_be_foreground
    def activate_input(self):
        """
        Sets up the input device if one was passed to the UI element - calling
        ``i.stop_listen``, ``self.configure_input`` and ``i.listen``. If an input
        element wasn't passed, checks if one is expected.
        """
        if self.i:
            self.i.stop_listen()
            self.configure_input()
            self.i.listen()
        else:
            if self._input_necessary:
                raise ValueError("UI element {} needs an input object supplied!")
            else:
                logger.warning("{}: no input device object supplied, not setting the keymap".format(self.name))

    @to_be_foreground
    def refresh(self):
        """
        Is called when the screen contents have to be updated.
        To be implemented by a child object.
        """
        raise NotImplementedError
