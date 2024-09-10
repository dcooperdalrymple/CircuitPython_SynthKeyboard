# SPDX-FileCopyrightText: 2017 Scott Shawcroft, written for Adafruit Industries
# SPDX-FileCopyrightText: Copyright (c) 2024 Cooper Dalrymple
#
# SPDX-License-Identifier: Unlicense

import asyncio

import board
from digitalio import DigitalInOut

from synthkeyboard import DebouncerKey, Keyboard

keyboard = Keyboard(
    keys=(
        DebouncerKey(
            DigitalInOut(board.USER_SW), inverted=True
        ),  # Pimoroni Pico Plus 2 BOOTSEL button
    )
)

keyboard.voice_press = lambda voice: print(f"Pressed: {voice.note.notenum:d}")
keyboard.voice_release = lambda voice: print(f"Released: {voice.note.notenum:d}")

asyncio.run(keyboard.update())
