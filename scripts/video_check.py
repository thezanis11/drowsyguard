"""Actual VideoCapture -> MediaPipe -> rules -> CSV, using a repeated portrait.

No real drowsiness labels or participant video: this is a software-path test.
"""
import csv
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def main():
    import cv2
    import numpy as np
    portrait = cv2.imread(str(ROOT / "data" / "portrait.jpg"))
    if portrait is None:
        raise FileNotFoundError("Run scripts/integration_check.py --download-fixture first")
    h, w = portrait.shape[:2]
    target_h = round(h * 640 / w) // 2 * 2
    portrait = cv2.resize(portrait, (640, target_h))
    video = ROOT / "data" / "portrait-blank-test.avi"
    writer = cv2.VideoWriter(str(video), cv2.VideoWriter_fourcc(*"MJPG"), 30, (640, target_h))
    if not writer.isOpened():
        raise RuntimeError("MJPG test writer unavailable")
    try:
        for _ in range(180):
            writer.write(portrait)
        for _ in range(30):
            writer.write(np.zeros_like(portrait))
    finally:
        writer.release()
    output = ROOT / "data" / f"video-check-{time.time_ns()}"
    process = subprocess.run([sys.executable, "-m", "drowsyguard", "run", "--video", str(video),
                              "--headless", "--output", str(output)], cwd=ROOT,
                             capture_output=True, text=True, encoding="utf-8", errors="replace")
    if process.returncode:
        raise RuntimeError(process.stdout + process.stderr)
    with (output / "metrics.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 210, len(rows)
    assert any(r["calibrated"] == "True" for r in rows), "Calibration did not complete"
    assert rows[-1]["state"] == "UNOBSERVABLE", rows[-1]
    assert not any(r["state"] == "ALERT" for r in rows), "Unexpected alarm on reference portrait"
    assert abs(float(rows[-1]["t"]) - 209/30) < 1e-8
    result = {"frames": len(rows), "calibration_completed": True,
              "final_state": rows[-1]["state"], "final_time_seconds": float(rows[-1]["t"]),
              "alerts": sum(r["state"] == "ALERT" for r in rows),
              "scope": "Repeated portrait followed by blank frames. Not a driver dataset.",
              "webcam_opened": False, "command_output": process.stdout}
    (ROOT / "reports" / "video-check.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
