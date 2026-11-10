"""MediaPipe adapter; does not infer a driver's medical/physiological state."""
from math import hypot, atan2, degrees, isfinite
from pathlib import Path
from .core import Observation

LEFT = (33, 160, 158, 133, 153, 144)
RIGHT = (362, 385, 387, 263, 373, 380)


def distance(a, b):
    return hypot(a[0] - b[0], a[1] - b[1])


def eye_ratio(points):
    width = distance(points[0], points[3])
    if width < 1e-8:
        raise ValueError("Degenerate eye geometry")
    return (distance(points[1], points[5]) + distance(points[2], points[4])) / (2 * width)


def measure(landmarks, width, height, t):
    if len(landmarks) < 468:
        return Observation(t, reason="INCOMPLETE_LANDMARKS"), []
    points = [(p.x * width, p.y * height) for p in landmarks]
    if any(not (isfinite(x) and isfinite(y)) for x, y in points):
        return Observation(t, reason="INVALID_GEOMETRY"), []
    face_width = distance(points[33], points[263])
    roll = abs(degrees(atan2(points[263][1] - points[33][1],
                             points[263][0] - points[33][0])))
    center = ((points[33][0] + points[263][0]) / 2,
              (points[33][1] + points[263][1]) / 2)
    # This is a geometric gate, not a calibrated head-pose estimation.
    asymmetry = abs(distance(points[1], points[33]) - distance(points[1], points[263])) / max(face_width, 1)
    important = [points[i] for i in (*LEFT, *RIGHT, 13, 14, 78, 308)]
    if any(not (0 <= x < width and 0 <= y < height) for x, y in important):
        reason = "FACE_OUT_OF_FRAME"
    elif face_width < 65:
        reason = "FACE_TOO_SMALL"
    elif roll > 30 or asymmetry > 0.40:
        reason = "POSE_UNRELIABLE"
    elif not (0.08 * width < center[0] < 0.92 * width):
        reason = "FACE_OUT_OF_FRAME"
    else:
        mouth_width = distance(points[78], points[308])
        if mouth_width < 1:
            return Observation(t, reason="DEGENERATE_FACE"), important
        try:
            ear = (eye_ratio([points[i] for i in LEFT]) + eye_ratio([points[i] for i in RIGHT])) / 2
        except ValueError:
            return Observation(t, reason="DEGENERATE_FACE"), []
        mar = distance(points[13], points[14]) / mouth_width
        return Observation(t, ear, mar, True, "VISIBLE"), important
    return Observation(t, reason=reason), important


class FaceTracker:
    def __init__(self, model):
        import mediapipe as mp
        from mediapipe.tasks import python
        from mediapipe.tasks.python import vision
        self.mp = mp
        # Buffer avoids non-ASCII model-path problems in some native builds.
        options = vision.FaceLandmarkerOptions(
            base_options=python.BaseOptions(model_asset_buffer=Path(model).read_bytes()),
            running_mode=vision.RunningMode.VIDEO, num_faces=2,
            min_face_detection_confidence=0.6, min_face_presence_confidence=0.6,
            min_tracking_confidence=0.6)
        self.detector = vision.FaceLandmarker.create_from_options(options)
        self.last_ms = -1

    def process(self, frame, t):
        import cv2
        image = self.mp.Image(image_format=self.mp.ImageFormat.SRGB,
                              data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        timestamp = max(self.last_ms + 1, round(t * 1000))
        self.last_ms = timestamp
        result = self.detector.detect_for_video(image, timestamp)
        if len(result.face_landmarks) != 1:
            reason = "MULTIPLE_FACES" if result.face_landmarks else "NO_FACE"
            return Observation(t, reason=reason), []
        h, w = frame.shape[:2]
        return measure(result.face_landmarks[0], w, h, t)

    def close(self):
        self.detector.close()

