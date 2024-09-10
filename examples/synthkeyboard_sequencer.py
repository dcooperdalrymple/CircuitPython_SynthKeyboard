# SPDX-FileCopyrightText: 2017 Scott Shawcroft, written for Adafruit Industries
# SPDX-FileCopyrightText: Copyright (c) 2024 Cooper Dalrymple
#
# SPDX-License-Identifier: Unlicense

import asyncio

from synthkeyboard import Keyboard, Sequencer

keyboard = Keyboard()

keyboard.on_voice_press = lambda voice: print(f"Pressed: {voice.note.notenum:d}")

sequencer = Sequencer()
sequencer.active = True

for i in range(4):
    sequencer.set_note(i * 4, 1)
    sequencer.set_note(i * 4 + 2, i % 2 + 2)

sequencer.on_press = lambda notenum, velocity: keyboard.append(notenum, velocity)
sequencer.on_release = lambda notenum: keyboard.remove(notenum)

asyncio.run(sequencer.update())
