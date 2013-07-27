#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import sys
sys.path.append("/usr/lib") # Arch Linux installs Leap.py here.

import time
from argparse import ArgumentParser

import Leap
from pymouse import PyMouse

from logger import Logger

class BasePointer(Leap.Listener):
    """Base class for converting events from the Leap into mouse events."""

    def __init__(self, mouse = None, logger = None):
        Leap.Listener.__init__(self)
        self.mouse = mouse or PyMouse()
        self.logger = logger or Logger()

    def on_init(self, controller):
        self.logger("debug", "Initialized")

    def on_connect(self, controller):
        self.logger("info", "Connected")
        controller.enable_gesture(Leap.Gesture.TYPE_KEY_TAP);

    def on_disconnect(self, controller):
        self.logger("info", "Disconnected")

    def on_exit(self, controller):
        self.logger("debug", "Exited")

    def on_frame(self, controller):
        frame = controller.frame()
        tap = False
        for gesture in frame.gestures():
            if gesture.type == Leap.Gesture.TYPE_KEY_TAP \
               and gesture.state == Leap.Gesture.STATE_STOP:
                tap = True
        self.update(frame, tap)

    def update(self, frame, tap):
        """Convert Leap frames into move() and click() events."""
        raise NotImplementedError # Implement in subclasses

    def move(self, x, y):
        """Adjust mouse position by the given relative distance (pixels)."""
        px, py = self.mouse.position()
        self.mouse.move(px + round(x), py + round(y))

    def click(self):
        """Perform a mouse click at the current position."""
        pos = self.mouse.position()
        self.mouse.click(*pos)
        self.logger("info", "Mouse click at (%d, %d)" % pos)

class HandPitchPointer(BasePointer):
    """Simple Pointer implementation using hand pitch/roll."""

    def __init__(self, mouse = None, logger = None):
        BasePointer.__init__(self, mouse, logger)
        self.mult = (5, 5) # multipliers on roll, pitch (radians)

    def update(self, frame, tap):
        if not frame.hands.empty:
            hand = frame.hands[0] # "first" hand only
            self.move(
                -hand.palm_normal.roll * self.mult[0],
                hand.direction.pitch * self.mult[1])
            self.logger("debug", "%10.3f: x: %+5.3f, y: %+5.3f %s" % (
                frame.timestamp / 1000000.0, # µs -> s
                hand.palm_normal.roll,
                hand.direction.pitch,
                "TAP!" if tap else ""))

class HandMovePointer(BasePointer):
    """Control mouse pointer using hand movement in the Leap's X/Y plane."""

    def __init__(self, mouse = None, logger = None):
        BasePointer.__init__(self, mouse, logger)
        self.mult = (4, 4) # multipliers on position delta (mm)
        self.timeout = 1.0 # forget previous frame after this long (s)
        self.max_vel = 2.0 # ignore velocity faster than this (m/s)
        self.max_accel = 100.0 # ignore acceleration greater than this (m/s²)
        self.min_tap_p = 0.2 # discard multiple taps within this long (s)
        self.prev_frame = None # previous frame
        self.prev_vel = 0 # previous velocity
        self.prev_tap = 0 # timestamp of last recorded tap

    def update(self, frame, tap):
        if frame.hands.empty: # Skip if no hands
            return
        p, self.prev_frame = self.prev_frame, frame
        if not p: # Skip if no previous frame to compare to
            return
        elapsed = max(0.000001, (frame.timestamp - p.timestamp) / 1000000.0)
        if elapsed > self.timeout: # Skip if too long since previous frame
            return
        d = frame.hands[0].palm_position - p.hands[0].palm_position # delta
        v = (d.magnitude / 1000.0) / elapsed # velocity (m/s)
        a = (v - self.prev_vel) / elapsed # acceleration (m/s²)
        self.prev_vel = v
        if v > self.max_vel or a > self.max_accel: # Skip on large v or a
            return

        if tap and frame.timestamp - self.prev_tap < self.min_tap_p * 1000000:
            tap = False
        if tap:
            self.prev_tap = frame.timestamp

        self.logger("debug", "%10.3f: %+5.1f, %+5.1f (%5.3fm/s, %8.3fm/s²) %s" % (
            frame.timestamp / 1000000.0, d.x, d.y, v, a, "TAP!" if tap else ""))
        self.move(d.x * self.mult[0], -d.y * self.mult[1])
        if tap:
            self.click()

PointerImpls = { 'move': HandMovePointer, 'pitch': HandPitchPointer, }

parser = ArgumentParser(description = "Use Leap Motion to control your mouse")
parser.add_argument("--pointer", choices=PointerImpls.keys(), default="move",
                    help="pointer mode ('move' follows hand movement, "
                         "'pitch' follows hand pitch/roll)")
parser.add_argument("--verbose", "-v", action="count", default=0,
                    help="increase verbosity (repeat for more effect)")
parser.add_argument("--quiet", "-q", action="count", default=0,
                    help="decrease verbosity (repeat for more effect)")

def main(args):
    sys.stdout = open("/dev/null", "w") # Prevent XLib output to console
    parsed_args = parser.parse_args(args)
    logger = Logger(
        threshold=Logger.threshold(parsed_args.verbose - parsed_args.quiet))
    pointer = PointerImpls[parsed_args.pointer](logger=logger)
    controller = Leap.Controller()

    controller.add_listener(pointer)

    # Sleep until interrupted by Ctrl-C
    logger("info", "Ctrl-C to quit...")
    try:
        while True:
            time.sleep(1000)
    except KeyboardInterrupt:
        pass
    finally:
        controller.remove_listener(pointer)

    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
