LeaPointer
==========

Use the Leap Motion as a mouse device.

Dependencies
------------

- Leap Motion SDK (https://www.leapmotion.com/developers)
- pymouse from PyUserInput (https://github.com/SavinaRoja/PyUserInput)
- Python ≥ v2.7 (http://python.org/download/)

Running
-------

1. Connect your Leap Motion device
2. Run 'leapd' (from the Leap Motion SDK)
3. Run 'LeaPointer.py' (use --help to see available options)

- Move your hand above the Leap Motion device to move the mouse pointer
- Do a key tap motion with a finger to generate a mouse click

Supported systems
-----------------

Should in theory run on all systems supported by the Leap Motion SDK and
pymouse (Windows, MacOS and Linux).

Tested on:

- Arch Linux, Python v2.7.5, Linux 3.10.2-1-ARCH,
  Leap Motion SDK v0.8.0 (build 5300)

License
-------

See the LICENSE file

Author
------

Johan Herland (johan@herland.net), based on the Leap Motion SDK documentation
