# SPDX-FileCopyrightText: 2017 Scott Shawcroft, written for Adafruit Industries
# SPDX-FileCopyrightText: Copyright (c) 2024 Cooper Dalrymple
#
# SPDX-License-Identifier: Unlicense

import adafruit_midi
import audiopwmio
import board
import digitalio
import synthio
import usb_midi
from adafruit_midi.control_change import ControlChange
from adafruit_midi.note_off import NoteOff
from adafruit_midi.note_on import NoteOn
from adafruit_midi.pitch_bend import PitchBend

import synthkeyboard

led = digitalio.DigitalInOut(board.LED)
led.direction = digitalio.Direction.OUTPUT

audio = audiopwmio.PWMAudioOut(board.A0)
synth = synthio.Synthesizer()
audio.play(synth)

notes = tuple([
    synthio.Note(
        frequency=440.0,
        bend=synthio.Math(synthio.MathOperation.SUM, synthio.LFO(rate=8.0, scale=0.0), 0.0, 0.0)
    ) for i in range(4)
])

keyboard = synthkeyboard.Keyboard(max_voices=len(notes))

def press(voice):
    notes[voice.index].frequency = synthio.midi_to_hz(voice.note.notenum)
    synth.press(notes[voice.index])
    led.value = True
keyboard.on_voice_press = press

def release(voice):
    synth.release(notes[voice.index])
    if not synth.pressed:
        led.value = False
keyboard.on_voice_release = release

midi = adafruit_midi.MIDI(
    midi_in=usb_midi.ports[0], in_channel=0, midi_out=usb_midi.ports[1], out_channel=0
)

while True:
    msg = midi.receive()
    if isinstance(msg, NoteOn) and msg.velocity != 0:
        keyboard.append(msg.note, msg.velocity / 127.0)
    elif isinstance(msg, NoteOff) or (isinstance(msg, NoteOn) and msg.velocity == 0):
        keyboard.remove(msg.note)
    elif isinstance(msg, ControlChange):
        if msg.control == 1: # Mod Wheel
            for note in notes:
                note.bend.a.scale = msg.value / 127 / 12.0
        elif msg.control == 64: # Sustain Pedal
            keyboard.sustain = msg.value >= 64
    elif isinstance(msg, PitchBend):
        for note in notes:
            note.bend.b = (msg.pitch_bend / 8192) - 1.0
