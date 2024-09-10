# SPDX-FileCopyrightText: 2017 Scott Shawcroft, written for Adafruit Industries
# SPDX-FileCopyrightText: Copyright (c) 2024 Cooper Dalrymple
#
# SPDX-License-Identifier: Unlicense

from synthkeyboard import Keyboard

keyboard = Keyboard()

keyboard.on_voice_press = lambda voice: print(f"Pressed: {voice.note.notenum:d}")
keyboard.on_voice_release = lambda voice: print(f"Released: {voice.note.notenum:d}")

for i in range(1, 4):
    keyboard.append(i)
for i in range(3, 0, -1):
    keyboard.remove(i)
