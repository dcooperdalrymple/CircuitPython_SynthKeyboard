# SPDX-FileCopyrightText: 2017 Scott Shawcroft, written for Adafruit Industries
# SPDX-FileCopyrightText: Copyright (c) 2024 Cooper Dalrymple
#
# SPDX-License-Identifier: MIT
"""
`synthkeyboard`
================================================================================

Tools to manage notes in musical applications. Includes note priority, arpeggiation, and sequencing.


* Author(s): Cooper Dalrymple

Implementation Notes
--------------------

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads

* Adafruit's SimpleMath library: https://github.com/adafruit/Adafruit_CircuitPython_SimpleMath
"""

# imports

__version__ = "0.0.0+auto.0"
__repo__ = "https://github.com/dcooperdalrymple/CircuitPython_SynthKeyboard.git"

import asyncio
import random
import time

try:
    from typing import Callable

    from circuitpython_typing.io import ROValueIO
except ImportError:
    pass


class KeyState:
    """An enum-like class representing states used by :class:`Key` and :class:`Keyboard`."""

    NONE: int = 0
    """Indicates that the key hasn't been activated in any way"""

    PRESS: int = 1
    """Indicates that the key has been pressed"""

    RELEASE: int = 2
    """Indicates that the key has been released"""


class Key:
    """An abstract layer to interface with the :class:`Keyboard` class."""

    def __init__(self):
        pass

    @property
    def state(self) -> int:
        """The current state as a constant value of :class:`KeyState`."""
        return KeyState.NONE

    @property
    def velocity(self) -> float:
        """Get the current velocity (0.0-1.0)."""
        return 1.0


class DebouncerKey(Key):
    """An abstract layer to debouncer sensor input to use physical key objects with the
    :class:`Keyboard` class. The Adafruit-CircuitPython-Debouncer module must be installed to use
    this class, else a ImportError will be thrown upon instantiation.

    :param io_or_predicate: The input pin or arbitrary predicate to debounce
    :int inverted: Whether or not to invert the state of the input. When invert is `False`, the
        signal is active-high. When it is `True`, the signal is active-low.
    """

    def __init__(self, io_or_predicate: ROValueIO | Callable[[], bool], inverted: bool = False):
        from adafruit_debouncer import Debouncer

        self._debouncer = Debouncer(io_or_predicate)
        self._inverted = inverted

    inverted: bool = False
    """Whether or not the state is inverted. When invert is `False`, the signal is active-high. When
    it is `True`, the signal is active-low.
    """

    @property
    def state(self) -> int:
        """The current state as a constant value of :class:`KeyState`. When accessed, the input pin
        or arbitraary predicate will be updated with basic debouncing.
        """
        self._debouncer.update()
        if self._debouncer.rose:
            return KeyState.PRESS if not self._inverted else KeyState.RELEASE
        elif self._debouncer.fell:
            return KeyState.RELEASE if not self._inverted else KeyState.PRESS
        else:
            return KeyState.NONE


class Note:
    """Object which represents the parameters of a note. Contains note number, velocity, key number
    (if evoked by a :class:`Key` object), and timestamp of when the note was created.

    :param notenum: The MIDI note number representing the frequency of a note.
    :param velocity: The strength of which a note was pressed from 0.0 to 1.0.
    :param keynum: The index number of the :class:`Key` object which created this :class:`Note`
        object.
    """

    def __init__(self, notenum: int, velocity: float = 1.0, keynum: int = None):
        self.notenum = notenum
        self.velocity = velocity
        self.keynum = keynum
        self.timestamp = time.monotonic()

    notenum: int = None
    """The MIDI note number representing the frequency of a note."""

    velocity: float = 1.0
    """The strength of which a note was pressed from 0.0 to 1.0."""

    keynum: int = None
    """The index number of the :class:`Key` object which created this :class:`Note` object."""

    @property
    def data(self) -> tuple[int, float, int]:
        """Return all note data as tuple. The data is formatted as: (notenum:int, velocity:float,
        keynum:int). Keynum may be set as `None` if not applicable.
        """
        return (self.notenum, self.velocity, self.keynum)

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.notenum == other.notenum
        elif isinstance(other, Voice):
            return self.notenum == other.note.notenum if not other.note is None else False
        elif type(other) == int:
            return self.notenum == other
        elif type(other) == list:
            for i in other:
                if self.__eq__(i):
                    return True
        return False

    def __ne__(self, other):
        if isinstance(other, self.__class__):
            return self.notenum != other.notenum
        elif isinstance(other, Voice):
            return self.notenum != other.note.notenum if not other.note is None else True
        elif type(other) == int:
            return self.notenum != other
        elif type(other) == list:
            for i in other:
                if not self.__ne__(i):
                    return False
            return True
        else:
            return False

    def __lt__(self, other):
        if isinstance(other, self.__class__):
            return self.notenum < other.notenum
        elif type(other) == int:
            return self.notenum < other
        else:
            return False

    def __gt__(self, other):
        if isinstance(other, self.__class__):
            return self.notenum > other.notenum
        elif type(other) == int:
            return self.notenum > other
        else:
            return False

    def __le__(self, other):
        if isinstance(other, self.__class__):
            return self.notenum <= other.notenum
        elif type(other) == int:
            return self.notenum <= other
        else:
            return False

    def __ge__(self, other):
        if isinstance(other, self.__class__):
            return self.notenum >= other.notenum
        elif type(other) == int:
            return self.notenum >= other
        else:
            return False


class Voice:
    """Object which represents the parameters of a :class:`Keyboard` voice. Used to allocate
    :class:`Note` objects to a pre-defined number of available slots in a logical manner based on
    timing and keyboard mode.

    :param index: The position of the voice in the pre-defined set of keyboard voices.
    """

    def __init__(self, index: int):
        self.index = index
        self.time = time.monotonic()

    index: int = None
    """The position of the voice in the pre-defined set of keyboard voices."""

    time: float = None
    """The last time in seconds at which a note was registered with this voice."""

    _note: Note = None

    @property
    def note(self) -> Note:
        """The :class:`Note` object assigned to this voice. When a note is assigned to a voice, the
        voice is "active" until the note is cleared by setting it to `None`.
        """
        return self._note

    @note.setter
    def note(self, value: Note) -> None:
        self._note = value
        if not value is None:
            self.time = time.monotonic()

    @property
    def active(self) -> bool:
        """The active state of the voice. Will return `True` if a note has been assigned to this
        voice.
        """
        return not self.note is None

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.index == other.index
        elif isinstance(other, Note) or type(other) == list:
            return self.note == other
        elif type(other) is int:
            return self.index == other  # NOTE: Use index or notenum?
        else:
            return False

    def __ne__(self, other):
        if isinstance(other, self.__class__):
            return self.index != other.index
        elif isinstance(other, Note) or type(other) == list:
            return self.note != other
        elif type(other) is int:
            return self.index != other  # NOTE: Use index or notenum?
        else:
            return False


class TimerStep:
    """An enum-like class representing common step divisions."""

    WHOLE: float = 0.25
    """Whole note beat division"""

    HALF: float = 0.5
    """Half note beat division"""

    QUARTER: float = 1.0
    """Quarter note beat division"""

    DOTTED_QUARTER: float = 1.5
    """Dotted quarter note beat division"""

    EIGHTH: float = 2.0
    """Eighth note beat division"""

    TRIPLET: float = 3.0
    """Triplet note beat division"""

    SIXTEENTH: float = 4.0
    """Sixteenth note beat division"""

    THIRTYSECOND: float = 8.0
    """Thirtysecond note beat division"""


class Timer:
    """An abstract class to help handle timing functionality of the :class:`Arpeggiator` and
    :class:`Sequencer` classes. Note press and release timing is managed by bpm (beats per minute),
    steps (divisions of a beat), and gate (note duration during step).

    :param bpm: The beats per minute of timer.
    :param steps: The number of steps to divide a single beat. The minimum value allowed is 0.25, or
        a whole note.
    :param gate: The duration of each pressed note per step to play before releasing as a ratio from
        0.0 to 1.0.
    """

    def __init__(self, bpm: float = 120.0, steps: float = TimerStep.EIGHTH, gate: float = 0.5):
        self._reset(False)
        self.gate = gate
        self.bpm = bpm
        self.steps = steps

    def _update_timing(self) -> None:
        self._step_time = 60.0 / self._bpm / self._steps
        self._gate_duration = self._gate * self._step_time

    def _reset(self, immediate=True):
        self._now = time.monotonic()
        if immediate:
            self._now -= self._step_time

    _bpm: float = 120.0

    @property
    def bpm(self) -> float:
        """Beats per minute."""
        return self._bpm

    @bpm.setter
    def bpm(self, value: float) -> None:
        self._bpm = max(value, 1.0)
        self._update_timing()

    _steps: float = TimerStep.EIGHTH

    @property
    def steps(self) -> float:
        """The number of steps per beat (or the beat division). The minimum value allowed is 0.25,
        or a whole note. The pre-defined :class:`TimerStep` constants can be used here.
        """
        return self._steps

    @steps.setter
    def steps(self, value: float) -> None:
        self._steps = max(value, TimerStep.WHOLE)
        self._update_timing()

    _gate: float = 0.5

    @property
    def gate(self) -> float:
        """The duration each pressed note per step will play before releasing within a step of a
        beat as a ratio of that step from 0.0 to 1.0.
        """
        return self._gate

    @gate.setter
    def gate(self, value: float) -> None:
        self._gate = min(max(value, 0.0), 1.0)
        self._update_timing()

    _active: bool = False

    @property
    def active(self) -> bool:
        """Whether or not the timer object is enabled (running)."""
        return self._active

    @active.setter
    def active(self, value: bool) -> None:
        if value == self._active:
            return
        self._active = value
        if self._active:
            self._now = time.monotonic() - self._step_time
        else:
            self._do_release()
        if self.enabled:
            self.enabled(self._active)

    enabled: Callable[[bool], None] = None
    """The callback method that is called when :attr:`active` is changed. Must have 1 parameter for
    the current active state. Ie: :code:`def enabled(active):`
    """

    step: Callable[[], None] = None
    """The callback method that is called when a step is triggered. This callback will fire whether
    or not the step has pressed any notes. However, any pressed notes will occur before this
    callback is called.
    """

    press: Callable[[int, float], None] = None
    """The callback method that is called when a timed step note is pressed. Must have 2 parameters
    for note value and velocity (0.0-1.0). Ie: :code:`def press(notenum, velocity):`.
    """

    release: Callable[[int], None] = None
    """The callback method that is called when a timed step note is released. Must have 1 parameter
    for note value. Velocity is always assumed to be 0.0. Ie: :code:`def release(notenum):`.
    """

    _last_press: list[int] = []

    async def update(self):
        """Update the timer object and call any relevant callbacks if a new beat step or the end of
        the gate of a step is reached. The actual functionality of this method will depend on the
        child class that utilizes the :class:`Timer` parent class.
        """
        while True:
            if not self._active:
                await self._sleep(0.01)
                continue
            self._update()
            self._do_step()
            if self._last_press:
                await self._sleep(self._gate_duration)
                self._do_release()
                await self._sleep(self._step_time - self._gate_duration)
            else:
                await self._sleep(self._step_time)

    async def _sleep(self, delay: float):
        self._now += delay
        await asyncio.sleep(self._now - time.monotonic())

    def _update(self):
        pass

    def _do_step(self):
        if self.step:
            self.step

    def _do_press(self, notenum, velocity):
        if self.press:
            self.press(notenum, velocity)
            self._last_press.append(notenum)

    def _do_release(self):
        if self.release and self._last_press:
            for notenum in self._last_press:
                self.release(notenum)
            self._last_press.clear()


class ArpeggiatorMode:
    """An enum-like class containing constaints for the possible modes of the :class:`Arpeggiator`
    class.
    """

    UP: int = 0
    """Play notes based on ascending note value."""

    DOWN: int = 1
    """Play notes based on descending note value."""

    UPDOWN: int = 2
    """Play notes based on note value in ascending order then descending order. The topmost and
    bottommost notes will not be repeated.
    """

    DOWNUP: int = 3
    """Play notes based on note value in descending order then ascending order. The topmost and
    bottommost notes will not be repeated.
    """

    PLAYED: int = 4
    """Play notes based on the time at which they were played (ascending)."""

    RANDOM: int = 5
    """Play notes in a random order."""


class Arpeggiator(Timer):
    """Use this class to iterate over notes based on time parameters. Note press and release timing
    is managed by bpm (beats per minute), steps (divisions of a beat), and gate (note duration
    during step).

    :param bpm: The beats per minute of timer.
    :param steps: The number of steps to divide a single beat. The minimum value allowed is 0.25, or
        a whole note.
    :param gate: The duration of each pressed note per step to play before releasing as a ratio from
        0.0 to 1.0.
    :param mode: The method of stepping through notes as specified by :class:`ArpeggiatorMode`
        constants.
    """

    def __init__(
        self, bpm: float = 120.0, steps: float = TimerStep.EIGHTH, mode: int = ArpeggiatorMode.UP
    ):
        Timer.__init__(
            self,
            bpm=bpm,
            steps=steps,
        )
        self.mode = mode

    _pos: int = 0

    def _reset(self, immediate=True):
        Timer._reset(self, immediate)
        self._pos = 0

    _octaves: int = 0

    @property
    def octaves(self) -> int:
        """The number of octaves in which to extend the notes, either up or down."""
        return self._octaves

    @octaves.setter
    def octaves(self, value: int) -> None:
        self._octaves = value
        if self._notes:
            self.notes = self._raw_notes

    _probability: float = 1.0

    @property
    def probability(self) -> float:
        """The likeliness that a note will be played within a step, ranging from 0.0 (never) to 1.0
        (always).
        """
        return self._probability

    @probability.setter
    def probability(self, value: float) -> None:
        self._probability = min(max(value, 0.0), 1.0)

    _mode: int = ArpeggiatorMode.UP

    @property
    def mode(self) -> int:
        """The method of stepping through notes. See :class:`ArpeggiatorMode` for options."""
        return self._mode

    @mode.setter
    def mode(self, value: int) -> None:
        self._mode = value % 6
        if self._notes:
            self.notes = self._raw_notes

    _raw_notes: list[Note] = []
    _notes: list[Note] = []

    def _get_notes(self, notes: list[Note] = []):
        if not notes:
            return notes

        if abs(self._octaves) > 0:
            l = len(notes)
            for octave in range(1, abs(self._octaves) + 1):
                for i in range(0, l):
                    notes.append(
                        Note(
                            notes[i].notenum + octave * (-1 if self._octaves < 0 else 1) * 12,
                            notes[i].velocity,
                        )
                    )

        if self._mode == ArpeggiatorMode.UP:
            notes.sort()
        elif self._mode == ArpeggiatorMode.DOWN:
            notes.sort(reverse=True)
        elif self._mode == ArpeggiatorMode.UPDOWN:
            notes.sort()
            if len(notes) > 2:
                _notes = notes[1:-1].copy()
                _notes.reverse()
                notes = notes + _notes
        elif self._mode == ArpeggiatorMode.DOWNUP:
            notes.sort(reverse=True)
            if len(notes) > 2:
                _notes = notes[1:-1].copy()
                _notes.reverse()
                notes = notes + _notes
        # PLAYED = notes stay as is, RANDOM = index is randomized on update

        return notes

    @property
    def notes(self) -> list[Note]:
        """The :class:`Note` objects which the arpeggiator is currently stepping through ordered as
        specified by :attr:`mode` and affected by :attr:`octaves`.
        """
        return self._notes

    @notes.setter
    def notes(self, value: list[Note]) -> None:
        if not self._notes:
            self._reset()
        self._raw_notes = value.copy()
        self._notes = self._get_notes(value)

    def _update(self):
        if self._notes:
            if self._probability < 1.0 and (
                self._probability == 0.0 or random.random() > self._probability
            ):
                return
            if self.mode == ArpeggiatorMode.RANDOM:
                self._pos = random.randrange(0, len(self._notes), 1)
            else:
                self._pos = (self._pos + 1) % len(self._notes)
            self._do_press(self._notes[self._pos].notenum, self._notes[self._pos].velocity)


class Sequencer(Timer):
    """Sequence notes using the :class:`Timer` class to create a multi-track note sequencer. By
    default, the Sequencer is set up for a single 4/4 measure of 16 notes with one track. Each note
    of each track can be assigned any note value and velocity. The length and number of tracks can
    be reassigned during runtime.

    :param length: The number of steps of each track. The minimum value allowed is 1.
    :param tracks: The number of tracks to create and sequence. The minimum value allowed is 1.
    :param bpm: The beats per minute of the timer.
    """

    def __init__(self, length: int = 16, tracks: int = 1, bpm: float = 120.0):
        Timer.__init__(self, bpm=bpm, steps=TimerStep.SIXTEENTH)
        self.length = length
        self.tracks = tracks
        self._data = [[None for j in range(self._length)] for i in range(self._tracks)]

    _data: list = None

    _length: int = 16

    @property
    def length(self) -> int:
        """The number of steps for each track. If the length is shortened, all of the step data
        beyond the new length will be deleted, and if the sequencer is also currently running, it
        should loop back around automatically to the start of the track data. The minimum allowed
        is 1.
        """
        return self._length

    @length.setter
    def length(self, value: int) -> None:
        value = max(value, 1)
        if self._data:
            if value > self._length:
                for i in range(self._tracks):
                    self._data[i] = self._data[i] + [None for j in range(value - self._length)]
            elif value < self._length:
                for i in range(self._tracks):
                    del self._data[i][value:]
        self._length = value

    _tracks: int = 1

    @property
    def tracks(self) -> int:
        """The number of note tracks to sequence. If the number of tracks is shortened, the tracks
        at an index greater to or equal than the number will be deleted. If a larger number of
        tracks is provided, the newly created tracks will be empty. The minimum allowed is 1.
        """
        return self._tracks

    @tracks.setter
    def tracks(self, value: int) -> None:
        value = max(value, 1)
        if self._data:
            if value > self._tracks:
                self._data = self._data + [
                    [None for j in range(self._length)] for i in range(value - self._tracks)
                ]
            elif value < self._tracks:
                del self._data[value:]
        self._tracks = value

    _pos: int = 0

    @property
    def position(self) -> int:
        """The current position of the sequencer within the track length (0-based)."""
        return self._pos

    def set_note(self, position: int, notenum: int, velocity: float = 1.0, track: int = 0) -> None:
        """Set the note value and velocity of a track at a specific step index.

        :param position: Index of the step (0-based). Will be limited to the track length.
        :param notenum: Value of the note.
        :param velocity: Velocity of the note (0.0-1.0).
        :param track: Index of the track (0-based). Will be limited to the track count.
        """
        track = min(max(track, 0), self._tracks)
        position = min(max(position, 0), self._length)
        self._data[track][position] = (notenum, velocity)

    def get_note(self, position: int, track: int = 0) -> tuple[int, int]:
        """Get the note data for a specified track and step position. If a note isn't defined at
        specific index, a value of `None` will be returned.

        :param position: Index of the step (0-based). Will be limited to the track length.
        :param track: Index of the track (0-based). Will be limited to the track count.
        :return: note data (notenum, velocity)
        """
        track = min(max(track, 0), self._tracks)
        position = min(max(position, 0), self._length)
        return self._data[track][position]

    def has_note(self, position: int, track: int = 0) -> bool:
        """Check whether or note a specific step within a track has been set with note data.

        :param position: Index of the step (0-based). Will be limited to the track length.
        :param track: Index of the track (0-based). Will be limited to the track count.
        :return: if the track step has a note
        """
        return not self.get_note(position, track) is None

    def remove_note(self, position: int, track: int = 0) -> None:
        """Remove the note data as a specific step within a track.

        :param position: Index of the step (0-based). Will be limited to the track length.
        :param track: Index of the track (0-based). Will be limited to the track count.
        """
        track = min(max(track, 0), self._tracks)
        position = min(max(position, 0), self._length)
        self._data[track][position] = None

    def get_track(self, track=0) -> list[tuple[int, int]]:
        """Get list of note data for a specified track index (0-based). If the track isn't
        available, a value of `None` will be returned.

        :return: track data list of note tuples as (notenum, velocity)
        """
        return self._data[min(max(track, 0), self._tracks)]

    step: Callable[[int], None] = None
    """The callback method that is called when a step is triggered. This callback will fire whether
    or not the step has any notes. However, any pressed notes will occur before this callback is
    called. Must have 1 parameter for sequencer position index. Ie: :code:`def step(pos):`.
    """

    def _update(self):
        self._pos = (self._pos + 1) % self._length
        for i in range(self._tracks):
            note = self._data[i][self._pos]
            if note and note[0] > 0 and note[1] > 0:
                self._do_press(note[0], note[1])

    def _do_step(self):
        if self.step:
            self.step(self._pos)


class KeyboardMode:
    """An enum-like class representing Keyboard note handling modes."""

    HIGH: int = 0
    """When the keyboard is set as this mode, it will prioritize the highest note value."""

    LOW: int = 1
    """When the keyboard is set as this mode, it will prioritize the lowest note value."""

    LAST: int = 2
    """When the keyboard is set as this mode, it will prioritize notes by the order in when they
    were played/appended.
    """


class Keyboard:
    """Manage notes, voice allocation, arpeggiator assignment, sustain, and relevant callbacks using
    this class.

    :param keys: A list of :class:`Key` objects which will be used to update the keyboard state.
    :param max_voices: The maximum number of voices/notes to be played at once.
    :param root: Set the base note number of the physical key inputs.
    """

    def __init__(
        self,
        keys: tuple[Key] = [],
        max_voices: int = 1,
        root: int = 48,
        mode: int = KeyboardMode.HIGH,
    ):
        self.root = root
        self._keys = keys
        self.mode = mode
        self.max_voices = max_voices
        self._voices = [Voice(i) for i in range(self.max_voices)]

    voice_press: Callable[[Voice], None] = None
    """The callback method to be called when a voice is pressed. Must have 1 parameter for the
    :class:`Voice` object. Ie: :code:`def press(voice):`.
    """

    voice_release: Callable[[Voice], None] = None
    """The callback method to be called when a voice is released. Must have 1 parameter for the
    :class:`Voice` object. Velocity is always assumed to be 0.0. Ie: :code:`def release(voice):`.
    """

    key_press: Callable[[int, int, float], None] = None
    """The callback method to be called when a :class:`Key` object is pressed. Must have 3
    parameters for keynum, note value, velocity (0.0-1.0), and keynum. Ie: :code:`def press(keynum,
    notenum, velocity):`.
    """

    key_release: Callable[[int, int], None] = None
    """The callback method to be called when a :class:`Key` object is released. Must have 2
    parameters for keynum and note value. Velocity is always assumed to be 0.0. Ie: :code:`def
    release(keynum, notenum):`.
    """

    _keys: tuple[Key] = None

    @property
    def keys(self) -> tuple[Key]:
        """The :class:`Key` objects which will be used to update the keyboard state."""
        return self._keys

    _arpeggiator: Arpeggiator = None

    @property
    def arpeggiator(self) -> Arpeggiator:
        """The :class:`Arpeggiator` object assigned to the keyboard."""
        return self._arpeggiator

    @arpeggiator.setter
    def arpeggiator(self, value: Arpeggiator) -> None:
        if self._arpeggiator:
            self._arpeggiator.press = None
            self._arpeggiator.release = None
        self._arpeggiator = value
        self._arpeggiator.enabled = self._timer_enabled
        self._arpeggiator.press = self._timer_press
        self._arpeggiator.release = self._timer_release

    _mode: int = KeyboardMode.HIGH

    @property
    def mode(self) -> int:
        """The note allocation mode. Use one of the mode constants of :class:`KeyboardMode`. Note
        allocation won't be updated until the next update call.
        """
        return self._mode

    @mode.setter
    def mode(self, value: int) -> None:
        self._mode = value % 3

    _sustain: bool = False
    _sustained: list[Note] = []

    @property
    def sustain(self) -> bool:
        """Whether or not the notes pressed are sustained after being released until this property
        is set to `False`.
        """
        return self._sustain

    @sustain.setter
    def sustain(self, value: bool) -> None:
        if value != self._sustain:
            self._sustain = value
            self._sustained = self._notes.copy() if self._sustain else []
            self._update()

    _notes: list[Note] = []

    @property
    def all_notes(self) -> list[Note]:
        """All active :class:`Note` objects."""
        return self._notes + self._sustained

    @property
    def notes(self) -> list[Note]:
        """Active :class:`Notes` objects according to the current :class:`KeyboardMode`."""
        notes = self.all_notes
        if self._mode in {KeyboardMode.HIGH, KeyboardMode.LOW}:
            notes.sort(reverse=(self._mode == KeyboardMode.HIGH))
        else:  # KeyboardMode.LAST
            notes.sort(key=lambda note: note.timestamp)
        return notes[: self._max_voices]

    def append(self, notenum: int | Note, velocity: float = 1.0, keynum: int = None):
        """Add a note to the keyboard buffer. Useful when working with MIDI input or another note
        source. Any previous notes with the same notenum value will be removed automatically.

        :param notenum: The number of the note. Can be defined by MIDI notes, a designated sample
            index, etc. When using MODE_HIGH or MODE_LOW, the value of this parameter will affect
            the order. A :class:`Note` object can be used instead of providing notenum, velocity,
            and keynum parameters directly.
        :param velocity: The velocity of the note from 0.0 through 1.0.
        :param keynum: An additional index reference typically used to associate the note with a
            physical :class:`Key` object. Not required for use of the keyboard.
        """
        self.remove(notenum, True)
        note = notenum if isinstance(notenum, Note) else Note(notenum, velocity, keynum)
        self._notes.append(note)
        if self._sustain:
            self._sustained.append(note)
        self._update()

    def remove(self, notenum: int | Note, remove_sustained: bool = False):
        """Remove a note from the keyboard buffer. Useful when working with MIDI input or another
        note source. If the note is found (and the keyboard isn't being sustained or
        remove_sustained is set as `True`), the release callback will trigger automatically
        regardless of the `update` parameter.

        :param notenum: The value of the note that you would like to be removed. All notes in the
            buffer with this value will be removed. Can be defined by MIDI note value, a designated
            sample index, etc. Can also use a :class:`Note` object instead.
        :param remove_sustained: Whether or not you would like to override the current sustained
            state of the keyboard and release any notes that are being sustained.
        """
        if not notenum in self.all_notes:
            return
        self._notes = [note for note in self._notes if note != notenum]
        if remove_sustained and self._sustain and self._sustained:
            self._sustained = [note for note in self._sustained if note != notenum]
        self._update()

    async def update(self, delay: float = 0.01) -> None:
        """Update :attr:`keys` objects if they were provided during initialization.

        :param delay: The amount of time to sleep between polling in seconds.
        """
        while self._keys:
            for i in range(len(self._keys)):
                state = self._keys[i].state
                if state == KeyState.NONE:
                    continue
                notenum = self.root + i
                if state == KeyState.PRESS:
                    velocity = self._keys[i].velocity
                    self.append(notenum, velocity, i)
                    if callable(self.key_press):
                        self.key_press(i, notenum, velocity)
                else:  # KeyState.RELEASE
                    self.remove(notenum)
                    if callable(self.key_release):
                        self.key_release(i, notenum)
            await asyncio.sleep(delay)

    def _update(self) -> None:
        if not self._arpeggiator or not self._arpeggiator.active:
            self._update_voices(self.notes)
        else:
            self._arpeggiator.notes = self.all_notes

    # Callbacks for arpeggiator
    def _timer_enabled(self, active: bool) -> None:
        if active:
            self.arpeggiator.notes = self.all_notes
        else:
            self.update()

    def _timer_press(self, notenum: int, velocity: float) -> None:
        self._update_voices([Note(notenum, velocity)])

    def _timer_release(self, notenum: int) -> None:  # NOTE: notenum is ignored
        self._update_voices()

    _voices: list[Voice] = []

    @property
    def voices(self) -> list[Voice]:
        """The :class:`Voice` objects used by the :class:`Keyboard` object."""
        return self._voices

    _max_voices: int = 1

    @property
    def max_voices(self) -> int:
        """The maximum number of voices used by this keyboard to allocate notes. Must be greater
        than 1. When this property is set, it will automatically release and delete any voices or
        add new voice objects depending on the previous number of voices. Any voice related
        callbacks may be triggered during this process.
        """
        return self._max_voices

    @max_voices.setter
    def max_voices(self, value: int) -> None:
        self._max_voices = max(value, 1)
        if len(self._voices) > self._max_voices:
            for i in range(len(self._voices) - 1, self._max_voices - 1, -1):
                self._release_voice(self._voices[i])
                del self._voices[i]
        elif len(self._voices) < self._max_voices:
            for i in range(len(self._voices), self._max_voices):
                self._voices.append(Voice(i))
        self._update_voices()

    @property
    def active_voices(self) -> list[Voice]:
        """All keyboard voices that are "active", have been assigned a note. The voices will
        automatically be sorted by the time they were last assigned a note from oldest to newest.
        """
        voices = [voice for voice in self._voices if voice.active]
        voices.sort(key=lambda voice: voice.time)
        return voices

    @property
    def inactive_voices(self) -> list[Voice]:
        """All keyboard voices that are "inactive", do not currently have a note assigned. The
        voices will automatically be sorted by the time they were last assigned a note from oldest
        to newest.
        """
        voices = [voice for voice in self._voices if not voice.active]
        voices.sort(key=lambda voice: voice.time)
        return voices

    def _update_voices(self, notes: list[Note] = None) -> None:
        # Release all active voices if no available notes
        if notes is None or not notes:
            if voices := self.active_voices:
                for voice in voices:
                    self._release_voice(voice)
            return

        if voices := self.active_voices:
            for voice in voices:
                # Determine if voice has one of the notes in the buffer
                has_note = False
                for note in notes:
                    if voice.note is note:
                        has_note = True
                        break
                if not has_note:
                    # Release voices without active notes
                    self._release_voice(voice)
                else:
                    # Remove currently active notes from buffer
                    notes.remove(voice.note)

        # Activate new notes
        # If no voices are available, it will ignore remaining notes
        if notes and (voices := self.inactive_voices):
            voice_index = 0
            for note in notes:
                self._press_voice(voices[voice_index], note)
                voice_index += 1
                if voice_index >= len(voices):
                    break

    def _press_voice(self, voice: Voice, note: Note) -> None:
        voice.note = note
        if self.voice_press:
            self.voice_press(voice)

    def _release_voice(self, voice: Voice | list):
        if type(voice) is list:
            for i in voice:
                self._release_voice(i)
        elif voice.active:
            if self.voice_release:
                self.voice_release(voice)
            voice.note = None
