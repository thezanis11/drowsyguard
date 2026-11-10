import math
import unittest
from drowsyguard.core import Config, Monitor, Observation
from drowsyguard.vision import eye_ratio


def visible(t, ear=.31, mouth=.08):
    return Observation(t, ear, mouth, True, "VISIBLE")


class TemporalRulesTests(unittest.TestCase):
    def test_short_blinks_do_not_trigger_continuous_closure(self):
        m = Monitor(calibrate=False)
        alerts = []
        for i in range(300):
            t = i / 30
            r = m.update(visible(t, .13 if 2 <= t < 2.2 or 5 <= t < 5.2 else .31))
            alerts.append(r.state)
        self.assertNotIn("ALERT", alerts)
        self.assertEqual(r.blinks, 2)

    def test_alarm_timing_is_independent_of_fps(self):
        first_alerts = []
        for fps in (10, 30, 60):
            m = Monitor(calibrate=False)
            alerts = []
            for i in range(fps * 4):
                t = i / fps
                r = m.update(visible(t, .13 if t >= 1 else .31))
                if r.state == "ALERT":
                    alerts.append(t)
            first_alerts.append(alerts[0])
        self.assertTrue(all(2.5 <= t <= 2.61 for t in first_alerts), first_alerts)

    def test_tracking_loss_breaks_closure_and_blink_continuity(self):
        m = Monitor(calibrate=False)
        for i in range(10):
            m.update(visible(i / 10, .13))
        r = m.update(Observation(1, reason="NO_FACE"))
        self.assertEqual(r.state, "UNOBSERVABLE")
        self.assertEqual(r.closed_seconds, 0)
        r = m.update(visible(1.1, .31))
        self.assertEqual(r.blinks, 0)
        self.assertEqual(r.closed_seconds, 0)

    def test_large_sampling_gap_is_unknown_not_sustained_closure(self):
        m = Monitor(calibrate=False)
        m.update(visible(0, .13))
        r = m.update(visible(10, .13))
        self.assertEqual(r.state, "UNOBSERVABLE")
        self.assertEqual(r.reason, "SAMPLING_GAP")
        self.assertEqual(r.valid_seconds, 0)
        self.assertEqual(r.closed_seconds, 0)

    def test_rollover_clips_intervals_at_window_boundary(self):
        cfg = Config(window_seconds=2, min_valid_seconds=1, max_gap=.35)
        m = Monitor(cfg, calibrate=False)
        for i in range(101):
            r = m.update(visible(i / 10))
        self.assertAlmostEqual(r.valid_seconds, 2)
        self.assertAlmostEqual(r.coverage, 1)
        self.assertEqual(r.closed_fraction, 0)

    def test_high_fraction_requires_enough_valid_time(self):
        cfg = Config(closure_seconds=5, window_seconds=10, min_valid_seconds=8)
        m = Monitor(cfg, calibrate=False)
        before = []
        after = []
        for i in range(121):
            t = i / 10
            r = m.update(visible(t, .13 if (i // 10) % 2 else .31))
            (before if t < 8 else after).append(r.reason)
        self.assertNotIn("HIGH_CLOSED_EYE_FRACTION", before)
        self.assertIn("HIGH_CLOSED_EYE_FRACTION", after)

    def test_missing_data_reduces_coverage(self):
        cfg = Config(closure_seconds=10, window_seconds=10, min_valid_seconds=1)
        m = Monitor(cfg, calibrate=False)
        for i in range(101):
            t = i / 10
            r = m.update(visible(t, .13) if t >= 6 else Observation(t))
        self.assertLess(r.coverage, .5)
        self.assertNotEqual(r.state, "ALERT")

    def test_mouth_is_warning_not_drowsiness_diagnosis(self):
        m = Monitor(calibrate=False)
        for i in range(45):
            r = m.update(visible(i / 10, mouth=.8))
        self.assertEqual(r.state, "WATCH")
        self.assertEqual(r.mouth_events, 1)
        r = m.update(visible(4.5))
        self.assertEqual(r.mouth_seconds, 0)
        self.assertEqual(r.mouth_events, 1)

    def test_invalid_numeric_landmarks_are_not_observable(self):
        m = Monitor(calibrate=False)
        r = m.update(visible(0, math.nan))
        self.assertIsNone(r.ear)
        self.assertEqual(r.state, "UNOBSERVABLE")

    def test_timestamp_validation(self):
        m = Monitor(calibrate=False)
        m.update(visible(1))
        for t in (1, .9, math.nan, math.inf, -1):
            with self.assertRaises(ValueError):
                m.update(visible(t))

    def test_calibration_derives_threshold_from_open_eye_reference(self):
        m = Monitor(Config(calibration_seconds=1, calibration_samples=10))
        for i in range(21):
            r = m.update(visible(i / 10, .32))
        self.assertTrue(r.calibrated)
        self.assertAlmostEqual(r.threshold, .224)

    def test_calibration_restarts_after_face_loss(self):
        m = Monitor(Config(calibration_seconds=2, calibration_samples=10))
        for i in range(15):
            m.update(visible(i / 10))
        m.update(Observation(1.5))
        for i in range(16, 30):
            r = m.update(visible(i / 10))
        self.assertFalse(r.calibrated)

    def test_bad_config_rejected(self):
        for kwargs in ({"ear_threshold": -1}, {"max_gap": math.inf},
                       {"min_coverage": 2}, {"window_seconds": 1}):
            with self.assertRaises(ValueError):
                Config(**kwargs)


class GeometryTests(unittest.TestCase):
    def test_eye_ratio_has_known_value_and_is_scale_invariant(self):
        points = [(0, 0), (1, 1), (3, 1), (4, 0), (3, -1), (1, -1)]
        self.assertAlmostEqual(eye_ratio(points), .5)
        self.assertAlmostEqual(eye_ratio([(3*x + 10, 3*y + 20) for x, y in points]), .5)

    def test_collapsed_eye_rejected(self):
        with self.assertRaises(ValueError):
            eye_ratio([(0, 0)] * 6)


if __name__ == "__main__":
    unittest.main()

