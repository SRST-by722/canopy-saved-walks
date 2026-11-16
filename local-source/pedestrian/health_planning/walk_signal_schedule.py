"""Explicit modelled pedestrian signals; no vehicle or measured-phase claims."""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class WalkProgram:
    red_s: float
    green_s: float
    clearance_s: float
    origin_s: float = 39600.

    def __post_init__(self):
        if not all(math.isfinite(v) and v > 0 for v in (self.red_s, self.green_s, self.clearance_s)):
            raise ValueError('Positive finite phase durations required')
        if not math.isfinite(self.origin_s):
            raise ValueError('Finite origin required')

    @property
    def period(self):
        return self.red_s + self.green_s + self.clearance_s


@dataclass(frozen=True)
class WalkGate:
    id: str
    program: WalkProgram
    margin_s: float = 2.

    def __post_init__(self):
        if not math.isfinite(self.margin_s) or self.margin_s < 0:
            raise ValueError('Invalid clearance margin')

    @property
    def windows(self):
        p = self.program
        return ((p.red_s, p.red_s + p.green_s, p.period),)

    def permitted(self, entry, crossing_s):
        if not math.isfinite(entry) or not math.isfinite(crossing_s) or crossing_s <= 0:
            raise ValueError('Finite clock and positive crossing duration required')
        phase = (entry - self.program.origin_s) % self.program.period
        a, b, c = self.windows[0]
        return a - 1e-8 <= phase < b - 1e-8 and phase + crossing_s + self.margin_s <= c + 1e-8

    def next_entry(self, arrival, crossing_s, deadline):
        if not all(math.isfinite(v) for v in (arrival, crossing_s, deadline)) or crossing_s <= 0:
            raise ValueError('Invalid entry request')
        p = self.program
        if crossing_s + self.margin_s > p.green_s + p.clearance_s:
            return None
        cycle = math.floor((arrival - p.origin_s) / p.period)
        while p.origin_s + cycle * p.period <= deadline:
            entry = max(arrival, p.origin_s + cycle * p.period + p.red_s)
            if self.permitted(entry, crossing_s) and entry + crossing_s <= deadline + 1e-8:
                return entry
            cycle += 1
        return None
