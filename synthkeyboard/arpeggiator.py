# SPDX-FileCopyrightText: 2017 Scott Shawcroft, written for Adafruit Industries
# SPDX-FileCopyrightText: Copyright (c) 2024 Cooper Dalrymple
#
# SPDX-License-Identifier: MIT

import random
from adafruit_simplemath import constrain
from synthkeyboard.timer import Timer, TimerStep

class ArpeggiatorMode:
    """An enum-like class containing constaints for the possible modes of the :class:`Arpeggiator` class."""

    UP:int = 0
    """Play notes based on ascending note value."""

    DOWN:int = 1
    """Play notes based on descending note value."""

    UPDOWN = 2
    """Play notes based on note value in ascending order then descending order. The topmost and bottommost notes will not be repeated."""

    DOWNUP = 3
    """Play notes based on note value in descending order then ascending order. The topmost and bottommost notes will not be repeated."""

    PLAYED = 4
    """Play notes based on the time at which they were played (ascending)."""

    RANDOM = 5
    """Play notes in a random order."""

class Arpeggiator(Timer):

    def __init__(self, bpm=120.0, steps=TimerStep.EIGHTH, mode=0, octaves=0, probability=1.0):
        Timer.__init__(self,
            bpm=bpm,
            steps=steps,
            gate=0.3
        )

        self._raw_notes = []
        self._notes = []

        self.set_mode(mode)
        self.set_octaves(octaves)
        self._probability = probability

        self._keyboard = None

    def _reset(self, immediate=True):
        Timer._reset(self, immediate)
        self._pos = 0

    def get_octaves(self):
        return self._octaves
    def set_octaves(self, value):
        self._octaves = int(value)
        if self._notes:
            self.update_notes(self._raw_notes)

    def get_probability(self):
        return self._probability
    def set_probability(self, value):
        self._probability = constrain(value, 0.0, 1.0)

    def set_keyboard(self, keyboard):
        self._keyboard = keyboard
    def _enable(self):
        if self._keyboard:
            self.update_notes(self._keyboard.get_notes())
    def _disable(self):
        if self._keyboard:
            self._keyboard.force_update()

    def get_mode(self):
        return self._mode
    def set_mode(self, value):
        self._mode = value % self.NUM_MODES
        if self._notes: self.update_notes(self._raw_notes)

    def _get_notes(self, notes=[]):
        if not notes: return notes

        if abs(self._octaves) > 0:
            l = len(notes)
            for octave in range(1,abs(self._octaves)+1):
                if self._octaves < 0:
                    octave = octave * -1
                for i in range(0,l):
                    notes.append(Note(notes[i].notenum + octave*12, notes[i].velocity))

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
    def update_notes(self, notes=[]):
        if not self._notes:
            self._reset()
        self._raw_notes = notes.copy()
        self._notes = self._get_notes(notes)

    def _update(self):
        if self._notes:
            if self._probability < 1.0 and (self._probability == 0.0 or random.random() > self._probability):
                return
            if self.get_mode() == ArpeggiatorMode.RANDOM:
                self._pos = random.randrange(0,len(self._notes),1)
            else:
                self._pos = (self._pos+1) % len(self._notes)
            self._do_press(self._notes[self._pos].notenum, self._notes[self._pos].velocity)
