Simple test
------------

Ensure your device works with this simple test.

.. literalinclude:: ../examples/synthkeyboard_simpletest.py
    :caption: examples/synthkeyboard_simpletest.py
    :linenos:

Keys
----

Use a digital input to trigger a note.

.. literalinclude:: ../examples/synthkeyboard_keys.py
    :caption: examples/synthkeyboard_keys.py
    :linenos:

Arpeggiator
-----------

Demonstration of the arpeggiator.

.. literalinclude:: ../examples/synthkeyboard_arpeggiator.py
    :caption: examples/synthkeyboard_arpeggiator.py
    :linenos:

Sequencer
---------

Demonstration of the sequencer.

.. literalinclude:: ../examples/synthkeyboard_sequencer.py
    :caption: examples/synthkeyboard_sequencer.py
    :linenos:

synthio & MIDI
--------------

Use the :class:`synthkeyboard.Keyboard` class to help allocate MIDI notes into a limited set of
:class:`synthio.Note` objects using USB MIDI input and DAC/PWM audio playback.

.. literalinclude:: ../examples/synthkeyboard_synthio.py
    :caption: examples/synthkeyboard_synthio.py
    :linenos:
