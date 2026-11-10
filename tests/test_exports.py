from pathlib import Path
import tempfile
import unittest
from drowsyguard.core import Monitor, Observation, Config
from drowsyguard.presentation import Recorder


class ExportTests(unittest.TestCase):
    def test_exports_are_local_numeric_and_refuse_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            recorder = Recorder(temp, "synthetic_observations")
            m = Monitor(calibrate=False)
            recorder.append(m.update(Observation(0, .3, .1, True)))
            recorder.append(m.update(Observation(.1, reason="NO_FACE")))
            recorder.close(Config())
            files = {p.name for p in Path(temp).iterdir()}
            self.assertEqual(files, {"metrics.csv", "summary.json", "report.html"})
            self.assertIn("synthetic_observations", (Path(temp) / "summary.json").read_text())
            with self.assertRaises(FileExistsError):
                Recorder(temp, "video")

