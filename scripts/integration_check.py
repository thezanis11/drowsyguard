"""Exercise the actual model on an official portrait and on blank images.

    python scripts/integration_check.py --download-fixture
The portrait checks the inference path, not somnolence accuracy.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from drowsyguard.assets import verify_model
from drowsyguard.vision import FaceTracker


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--download-fixture", action="store_true")
    args = parser.parse_args()
    image_path = ROOT / "data" / "portrait.jpg"
    url = "https://storage.googleapis.com/mediapipe-assets/portrait.jpg"
    if args.download_fixture and not image_path.exists():
        image_path.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(url, timeout=60) as response:
            data = response.read(5 * 1024 * 1024 + 1)
        if len(data) > 5 * 1024 * 1024:
            raise ValueError("Fixture exceeds 5 MB")
        image_path.write_bytes(data)
    if not image_path.exists():
        raise FileNotFoundError("Run with --download-fixture for the official MediaPipe test portrait")
    import cv2
    import numpy as np
    frame = cv2.imread(str(image_path))
    assert frame is not None, "Portrait not decodable"
    h, w = frame.shape[:2]
    frame = cv2.resize(frame, (640, round(h * 640 / w)))
    start = time.perf_counter()
    tracker = FaceTracker(verify_model())
    try:
        obs, points = tracker.process(frame, 0)
        assert obs.valid, f"Portrait not observable: {obs}"
        assert len(points) == 16
        blank, _ = tracker.process(np.zeros_like(frame), .1)
        # Tracking may persist for a single blank frame; use repeated blanks.
        for i in range(2, 12):
            blank, _ = tracker.process(np.zeros_like(frame), i / 10)
        assert not blank.valid, "Blank image must not provide observable eyes"
    finally:
        tracker.close()
    results = {"portrait_observation": obs.__dict__, "blank_observation": blank.__dict__,
               "wall_seconds": time.perf_counter() - start,
               "fixture_url": url, "fixture_sha256": hashlib.sha256(image_path.read_bytes()).hexdigest(),
               "scope": "Real model load + static portrait + blank frames. Not drowsiness validation.",
               "webcam_opened": False}
    out = ROOT / "reports"
    out.mkdir(exist_ok=True)
    (out / "integration.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()

