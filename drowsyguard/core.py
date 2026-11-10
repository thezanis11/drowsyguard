"""Time-based rules, independent of the camera and landmark library."""
from collections import deque
from dataclasses import dataclass, asdict
from math import isfinite
from statistics import quantiles


@dataclass(frozen=True)
class Config:
    ear_threshold: float = 0.21
    closure_seconds: float = 1.5
    mouth_threshold: float = 0.60
    mouth_seconds: float = 2.0
    window_seconds: float = 30.0
    closed_fraction_threshold: float = 0.28
    min_valid_seconds: float = 15.0
    min_coverage: float = 0.80
    max_gap: float = 0.35
    calibration_seconds: float = 5.0
    calibration_samples: int = 40
    calibration_ratio: float = 0.70

    def __post_init__(self):
        for key, value in asdict(self).items():
            if not isfinite(value) or value <= 0:
                raise ValueError(f"{key} must be finite and positive")
        if self.min_valid_seconds > self.window_seconds:
            raise ValueError("min_valid_seconds exceeds the rolling window")
        if any(v > 1 for v in (self.closed_fraction_threshold, self.min_coverage,
                              self.calibration_ratio, self.ear_threshold)):
            raise ValueError("Ratios must be <= 1")


@dataclass(frozen=True)
class Observation:
    t: float
    ear: float | None = None
    mouth: float | None = None
    valid: bool = False
    reason: str = "NO_FACE"

    def usable(self):
        return (self.valid and self.ear is not None and self.mouth is not None
                and isfinite(self.ear) and isfinite(self.mouth)
                and 0 < self.ear < 1 and 0 <= self.mouth < 3)


@dataclass(frozen=True)
class Reading:
    t: float
    state: str
    reason: str
    ear: float | None
    mouth: float | None
    threshold: float
    closed_seconds: float
    closed_fraction: float | None
    coverage: float
    valid_seconds: float
    mouth_seconds: float
    blinks: int
    mouth_events: int
    calibrated: bool


class Monitor:
    """A left-sample time integral; large gaps are unknown, never open eyes.

    Both endpoints must be observable for an interval to count as measured.
    This deliberately excludes intervals at the edge of a tracking loss.
    """
    def __init__(self, config=None, calibrate=True):
        self.cfg = config or Config()
        self.calibrate = calibrate
        self.threshold = self.cfg.ear_threshold
        self.calibrated = not calibrate
        self.calibration_start = None
        self.samples = []
        self.prev = None
        self.first = None
        self.intervals = deque()
        self.eye_start = self.mouth_start = None
        self.mouth_counted = False
        self.blinks = self.mouth_events = 0

    def update(self, obs):
        if not isfinite(obs.t) or obs.t < 0:
            raise ValueError("Timestamp must be finite and non-negative")
        if self.prev is not None and obs.t <= self.prev.t:
            raise ValueError("Timestamps must strictly increase")
        usable = obs.usable()
        dt = 0 if self.prev is None else obs.t - self.prev.t
        continuous = (self.prev is not None and usable and self.prev.usable()
                      and dt <= self.cfg.max_gap)
        if self.first is None:
            self.first = obs.t
        if not self.calibrated:
            if not usable or (self.prev is not None and dt > self.cfg.max_gap):
                self.samples.clear()
                self.calibration_start = None
            if usable:
                if self.calibration_start is None:
                    self.calibration_start = obs.t
                self.samples.append(obs.ear)
                # Keep a bounded sample buffer even if calibration never succeeds.
                self.samples = self.samples[-1800:]
                if (obs.t - self.calibration_start >= self.cfg.calibration_seconds
                        and len(self.samples) >= self.cfg.calibration_samples):
                    baseline = quantiles(self.samples, n=4, method="inclusive")[2]
                    if 0.15 <= baseline <= 0.50:
                        self.threshold = max(0.12, min(0.32, baseline * self.cfg.calibration_ratio))
                        self.calibrated = True
                        self.first = obs.t
                        self.intervals.clear()
                    else:
                        self.samples.clear()
                        self.calibration_start = None
            self.prev = obs
            return self._reading(obs, "CALIBRATING" if not self.calibrated else "MONITORING",
                                 "KEEP_EYES_OPEN" if usable else obs.reason)

        if self.prev is not None:
            previous_closed = self.prev.usable() and self.prev.ear < self.threshold
            self.intervals.append((self.prev.t, obs.t, continuous, previous_closed))
        cutoff = obs.t - self.cfg.window_seconds
        while self.intervals and self.intervals[0][1] <= cutoff:
            self.intervals.popleft()

        if not continuous:
            self.eye_start = self.mouth_start = None
            self.mouth_counted = False
        if usable:
            if obs.ear < self.threshold:
                if self.eye_start is None:
                    self.eye_start = obs.t
            else:
                if continuous and self.eye_start is not None:
                    duration = obs.t - self.eye_start
                    if 0.08 <= duration <= 0.8:
                        self.blinks += 1
                self.eye_start = None
            if obs.mouth > self.cfg.mouth_threshold:
                if self.mouth_start is None:
                    self.mouth_start = obs.t
                if obs.t - self.mouth_start >= self.cfg.mouth_seconds and not self.mouth_counted:
                    self.mouth_events += 1
                    self.mouth_counted = True
            else:
                self.mouth_start = None
                self.mouth_counted = False
        else:
            self.eye_start = self.mouth_start = None

        reading = self._reading(obs, "MONITORING", "NO_RULE_TRIGGERED")
        self.prev = obs
        if not usable:
            return self._reading(obs, "UNOBSERVABLE", "INVALID_METRICS" if obs.valid else obs.reason)
        if dt > self.cfg.max_gap:
            return self._reading(obs, "UNOBSERVABLE", "SAMPLING_GAP")
        if reading.closed_seconds >= self.cfg.closure_seconds:
            return self._reading(obs, "ALERT", "PROLONGED_EYE_CLOSURE")
        if (reading.closed_fraction is not None
                and reading.valid_seconds >= self.cfg.min_valid_seconds
                and reading.coverage >= self.cfg.min_coverage
                and reading.closed_fraction >= self.cfg.closed_fraction_threshold):
            return self._reading(obs, "ALERT", "HIGH_CLOSED_EYE_FRACTION")
        if reading.mouth_seconds >= self.cfg.mouth_seconds:
            return self._reading(obs, "WATCH", "PROLONGED_MOUTH_OPENING")
        return reading

    def _reading(self, obs, state, reason):
        cutoff = obs.t - self.cfg.window_seconds
        measured = closed = 0.0
        for start, end, valid, eye_closed in self.intervals:
            seconds = max(0.0, end - max(start, cutoff))
            if valid:
                measured += seconds
                if eye_closed:
                    closed += seconds
        elapsed = min(self.cfg.window_seconds, max(0, obs.t - self.first))
        return Reading(obs.t, state, reason, obs.ear if obs.usable() else None,
                       obs.mouth if obs.usable() else None, self.threshold,
                       0.0 if self.eye_start is None else obs.t - self.eye_start,
                       closed / measured if measured > 0 else None,
                       measured / elapsed if elapsed > 0 else 0.0, measured,
                       0.0 if self.mouth_start is None else obs.t - self.mouth_start,
                       self.blinks, self.mouth_events, self.calibrated)

