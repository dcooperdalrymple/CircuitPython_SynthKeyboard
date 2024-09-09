# SPDX-FileCopyrightText: 2017 Scott Shawcroft, written for Adafruit Industries
# SPDX-FileCopyrightText: Copyright (c) 2024 Cooper Dalrymple
#
# SPDX-License-Identifier: MIT

import time
from adafruit_simplemath import constrain

class TimerStep:
    """An enum-like class representing common step divisions."""

    WHOLE:float = 0.25
    """Whole note beat division"""

    HALF:float = 0.5
    """Half note beat division"""

    QUARTER:float = 1.0
    """Quarter note beat division"""

    DOTTED_QUARTER:float = 1.5
    """Dotted quarter note beat division"""

    EIGHTH:float = 2.0
    """Eighth note beat division"""

    TRIPLET:float = 3.0
    """Triplet note beat division"""

    SIXTEENTH:float = 4.0
    """Sixteenth note beat division"""

    THIRTYSECOND:float = 8.0
    """Thirtysecond note beat division"""

class Timer:
    """An abstract class to help handle timing functionality of the :class:`arpeggiator.Arpeggiator` and :class:`sequencer.Sequencer` classes. Note press and release timing is managed by bpm (beats per minute), steps (divisions of a beat), and gate (note duration during step).

    :param bpm: The beats per minute of timer.
    :type bpm: int
    :param steps: The number of steps to divide a single beat. The minimum value allowed is 0.25, or a whole note.
    :type steps: float
    :param gate: The duration of each pressed note per step to play before releasing. This value is a ratio from 0.0 to 1.0.
    :type gate: float
    """

    def __init__(self, bpm=120.0, steps=2.0, gate=0.5):
        self._enabled = False
        self._gate = constrain(gate, 0.0, 1.0)

        self._reset(False)
        self._update_timing(
            bpm=bpm,
            steps=max(float(steps), TimerStep.WHOLE)
        )

        self._step = None
        self._press = None
        self._release = None
        self._last_press = []

    def _update_timing(self, bpm=None, steps=None):
        if bpm: self._bpm = bpm
        if steps: self._steps = steps
        self._step_time = 60.0 / self._bpm / self._steps
        self._gate_duration = self._gate * self._step_time

    def _reset(self, immediate=True):
        self._now = time.monotonic()
        if immediate:
            self._now -= self._step_time

    def set_bpm(self, value):
        """Set the beats per minute.

        :param value: The desired beats per minute.
        :type value: int
        """
        self._update_timing(bpm=value)
    def get_bpm(self):
        """Get the beats per minute.

        :return: Beats per minute
        :rtype: int
        """
        return self._bpm

    def set_steps(self, value:float):
        """Set number of steps per beat (or the beat division). The pre-defined :class:`TimerStep` constants can be used here.

        :param value: The number of steps to divide a single beat. The minimum value allowed is 0.25, or a whole note.
        :type value: float
        """
        value = max(float(value), TimerStep.WHOLE)
        self._update_timing(steps=value)
    def get_steps(self):
        """Get the number of steps per beat (or the beat division).

        :return: Steps per beat
        :rtype: float
        """
        return self._steps

    def set_gate(self, value):
        """Set the note gate within a step of a beat.

        :param value: The duration of each pressed note per step to play before releasing. This value is a ratio from 0.0 to 1.0.
        :type value: float
        """
        self._gate = constrain(value, 0.0, 1.0)
        self._update_timing()
    def get_gate(self):
        """Get the note gate within a step of a beat. This value is a ratio from 0.0 to 1.0.

        :return: gate
        :rtype: float
        """
        return self._gate

    def is_enabled(self):
        """Whether or not the timer object is enabled (running).

        :return: enabled state
        :rtype: bool
        """
        return self._enabled
    def set_enabled(self, value:bool):
        """Directly set whether or not the timer object is enabled (running).

        :param value: The state of the timer.
        :type value: bool
        """
        if value and not self._enabled:
            self.enable()
        elif not value and self._enabled:
            self.disable()
    def enable(self):
        """Enable the timer object to start timing beat steps and triggering note press and release callbacks. The first step will immediately trigger.
        """
        self._enabled = True
        self._now = time.monotonic() - self._step_time
        self._enable()
    def _enable(self):
        pass
    def disable(self):
        """Disable the timer object and immediately release any pressed notes.
        """
        self._enabled = False
        self._do_release()
        self._disable()
    def _disable(self):
        pass
    def toggle(self):
        """Toggle between the enabled and disabled timer states. Any relevant actions may occur during this process (note press and release callbacks).
        """
        if self.is_enabled():
            self.disable()
        else:
            self.enable()

    def set_step(self, callback):
        """Set the callback method you would like to be called when a step is triggered. This callback will fire whether or not the step has pressed any notes. However, any pressed notes will occur before this callback is called.

        :param callback: The callback method without any parameters. Ie: `def step():`.
        :type callback: function
        """
        self._step = callback
    def set_press(self, callback):
        """Set the callback method you would like to be called when a timed step note is pressed.

        :param callback: The callback method. Must have 2 parameters for note value and velocity (0.0-1.0). Ie: `def press(notenum, velocity):`.
        :type callback: function
        """
        self._press = callback
    def set_release(self, callback):
        """Set the callback method you would like to be called when a timed step note is released.

        :param callback: The callback method. Must have 1 parameter for note value. Velocity is always assumed to be 0.0. Ie: `def release(notenum):`.
        :type callback: function
        """
        self._release = callback

    def _is_active(self):
        return self._enabled

    def update(self):
        """Update the timer object and call any relevant callbacks if a new beat step or the end of the gate of a step is reached. The actual functionality of this method will depend on the child class that utilizes the :class:`Timer` parent class.
        """
        while True:
            if not self._is_active():
                break
            self._update()
            self._do_step()
            if self._last_press:
                self.sleep(self._gate_duration)
                self._do_release()
                self.sleep(self._step_time - self._gate_duration)
            else:
                self.sleep(self._step_time)
    def sleep(self, delay:float):
        self._now += delay
        time.sleep(self._now - time.monotonic())

    def _update(self):
        pass

    def _do_step(self):
        if self._step:
            self._step()
    def _do_press(self, notenum, velocity):
        if self._press:
            self._press(notenum, velocity)
            self._last_press.append(notenum)
    def _do_release(self):
        if self._release and self._last_press:
            for notenum in self._last_press:
                self._release(notenum)
            self._last_press.clear()
