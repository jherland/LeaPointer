#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import sys
import math
import time
from argparse import ArgumentParser

sys.path.append("/usr/lib") # Arch Linux installs Leap.py here.

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

    class State(object):
        def __init__(self, frame, tap, prev):
            self.tap = tap
            self.ts = frame.timestamp / 1000000.0 # (s)

            NaN = float('NaN')
            self.nfingers = 0
            self.pos = NaN # (mm)
            self.elapsed = NaN # (s)
            self.d_pos = Leap.Vector(NaN, NaN, NaN) # (mm)
            self.vel = NaN # (mm/s)
            self.accel = NaN # (mm/s²)
            # BATMAN!
            try:
                fingers = frame.hands[0].fingers
                self.nfingers = len(fingers)
                # Calculate average finger tip position
                self.pos = sum((f.tip_position for f in fingers),
                               Leap.Vector()) / len(fingers)
                self.elapsed = max(0.000001, self.ts - prev.ts)
                self.d_pos = self.pos - prev.pos
                self.vel = self.d_pos.magnitude / self.elapsed
                self.accel = (self.vel - prev.vel) / self.elapsed
            except:
                pass

        def __str__(self):
            return ("{self.ts:10.3f}: "
                    "({self.d_pos.x:+5.1f}, {self.d_pos.y:+5.1f})mm "
                    "in {self.elapsed:5.3f}s ({self.nfingers} fingers)"
                    " => {self.vel:10.3f}mm/s, {self.accel:11.3f}mm/s² {tap}"
                    ).format(self=self, tap="TAP!" if self.tap else "")

    def __init__(self, mouse = None, logger = None):
        BasePointer.__init__(self, mouse, logger)
        self.timeout = 1.0 # forget previous frame after this long (s)
        self.max_vel = 2000 # ignore velocity faster than this (mm/s)
        self.max_accel = 100000 # ignore acceleration greater than this (mm/s²)
        self.min_tap_p = 0.2 # discard multiple taps within this long (s)
        self.finger_pause = 0.1 # pause movement when #fingers changes (s)

        self.prev = None # previous state
        self.last_tap = 0 # timestamp of last tap
        self.last_change = 0 # timestamp of last #fingers change

    def multiplier(self, nfingers):
        # multiplier on d_pos determined by #fingers - fewer fingers -> faster
        if nfingers <= 0:
            return 0
        else:
            return 16.0 / (nfingers ** 2)

    def update(self, frame, tap):
        p, s = self.prev, self.State(frame, tap, self.prev)
        self.prev = s

        if (math.isnan(s.accel) # could not calculate acceleration
            or s.elapsed > self.timeout # too long since last update
            or s.vel > self.max_vel # velocity too high
            or abs(s.accel) > self.max_accel): # acceleration too high
            return

        if p and s.nfingers != p.nfingers:
            self.last_change = s.ts
        if s.ts - self.last_change < self.finger_pause:
            s.d_pos *= 0 # don't move pointer when #fingers changes

        if s.tap and s.ts - self.last_tap < self.min_tap_p:
            s.tap = False # ignore repeated taps within a self.min_tap_p
        if s.tap:
            self.last_tap = s.ts

        self.logger("debug", s)
        s.d_pos *= self.multiplier(s.nfingers)
        self.move(s.d_pos.x, -s.d_pos.y)
        if s.tap:
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
