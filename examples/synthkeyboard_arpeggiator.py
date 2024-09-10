# SPDX-FileCopyrightText: 2017 Scott Shawcroft, written for Adafruit Industries
# SPDX-FileCopyrightText: Copyright (c) 2024 Cooper Dalrymple
#
# SPDX-License-Identifier: Unlicense

import asyncio

from synthkeyboard import Arpeggiator, ArpeggiatorMode, Keyboard, TimerStep

keyboard = Keyboard()

keyboard.on_voice_press = lambda voice: print(f"Pressed: {voice.note.notenum:d}")

keyboard.arpeggiator = Arpeggiator(steps=TimerStep.QUARTER, mode=ArpeggiatorMode.UPDOWN)
keyboard.arpeggiator.octaves = 1
keyboard.arpeggiator.active = True

for i in range(1, 4):
    keyboard.append(i)

asyncio.run(keyboard.arpeggiator.update())
