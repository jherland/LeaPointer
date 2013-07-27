import sys

class Logger(object):
    """General purpose logging to console/file with log levels.

    The log threshold is configurable, and determines which messages are
    output (level <= threshold), and which are discarded (level > threshold).
    """

    Levels = [ "error", "warning", "info", "debug" ] # High -> low importance
    Threshold = "info" # Default threshold, override in constructor

    @classmethod
    def limit(cls, val, maximum=len(Levels), minimum=0):
        """Limit val to [minimum, maximum)."""
        return max(minimum, val) if val < maximum else maximum - 1

    @classmethod
    def threshold(cls, adjust=0, default=Threshold):
        """Calculate new threshold by applying an adjustment to the default."""
        return cls.Levels[cls.limit(cls.Levels.index(default) + adjust)]

    def __init__(self, f=sys.stderr, threshold=Threshold):
        self.f = f
        self.t = self.Levels.index(threshold)

    def __call__(self, level, msg):
        """Print msg if level <= threshold."""
        if self.Levels.index(level) <= self.t:
            print >>self.f, msg
