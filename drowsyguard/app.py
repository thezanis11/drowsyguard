import argparse
from dataclasses import asdict
import json
from pathlib import Path
import time

from .assets import ROOT, verify_model, download_model
from .core import Config, Monitor, Observation
from .presentation import AudioAlert, Recorder, draw_dashboard


def synthetic_observations():
    """Explicitly fabricated signals: no camera and no landmark inference."""
    for index in range(900):
        t = index / 30
        missing = 12 <= t < 15
        closed = (5 <= t < 5.2 or 8 <= t < 10.2 or 18 <= t < 20
                  or 22 <= t < 24 or 26 <= t < 29)
        yield Observation(t, .13 if closed else .31, .78 if 15 <= t < 17.5 else .08,
                          not missing, "NO_FACE" if missing else "VISIBLE")


def config_from_args(args):
    values = {}
    if args.config:
        values = json.loads(Path(args.config).read_text(encoding="utf-8"))
    if args.ear_threshold is not None:
        values["ear_threshold"] = args.ear_threshold
    return Config(**values)


def demo(args, config):
    import cv2
    import numpy as np
    monitor = Monitor(config, calibrate=False)
    recorder = Recorder(args.output, "synthetic_observations") if args.output else None
    last = None
    try:
        for obs in synthetic_observations():
            reading = monitor.update(obs)
            frame = np.zeros((480, 640, 3), np.uint8)
            frame[:] = (45, 35, 25)
            cv2.putText(frame, "SYNTHETIC SIGNAL DEMO", (80, 235), cv2.FONT_HERSHEY_SIMPLEX,
                        .9, (210, 230, 240), 2, cv2.LINE_AA)
            display = draw_dashboard(frame, reading, fps=30, demo=True)
            if recorder:
                recorder.append(reading)
                if reading.state == "ALERT" and last is None:
                    cv2.imwrite(str(recorder.path / "demo-alert.png"), display)
                    last = reading
            if not args.headless:
                cv2.imshow("DrowsyGuard - demonstration", display)
                if cv2.waitKey(30) & 0xFF in (ord('q'), 27):
                    break
        print("Démo synthétique terminée : logique temporelle uniquement.")
    finally:
        if recorder:
            recorder.close(config)
        cv2.destroyAllWindows()


def run(args, config):
    import cv2
    from .vision import FaceTracker
    if args.headless and args.video is None:
        raise ValueError("Le mode sans fenêtre nécessite --video (ou la commande demo)")
    if args.camera < 0:
        raise ValueError("Indice de caméra négatif")
    source = str(Path(args.video).resolve()) if args.video else args.camera
    if args.video and not Path(args.video).is_file():
        raise FileNotFoundError("Vidéo introuvable")
    model = verify_model()  # No implicit download during camera use.
    recorder = Recorder(args.output, "video" if args.video else "webcam") if args.output else None
    cap = tracker = None
    monitor = Monitor(config, calibrate=not args.no_calibrate)
    audio = AudioAlert(not args.mute and not args.headless)
    processed = 0
    previous_state = None
    started = time.monotonic()
    try:
        cap = cv2.VideoCapture(source)
        if not cap.isOpened():
            raise RuntimeError("Impossible d'ouvrir la source. Vérifiez caméra, autorisation et indice --camera.")
        if not args.video:
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 960)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 540)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        rate = cap.get(cv2.CAP_PROP_FPS)
        if args.video and (rate <= 0 or rate > 1000):
            raise ValueError("Cadence vidéo invalide : les durées ne peuvent pas être établies")
        tracker = FaceTracker(model)
        started = time.monotonic()
        while True:
            tick = time.monotonic()
            ok, frame = cap.read()
            if not ok:
                if args.video:
                    break
                raise RuntimeError("Flux caméra interrompu : surveillance arrêtée")
            t = processed / rate if args.video else time.monotonic() - started
            # Bound inference resolution, preserving aspect ratio.
            h, w = frame.shape[:2]
            if w > 960:
                frame = cv2.resize(frame, (960, round(h * 960 / w)))
            obs, points = tracker.process(frame, t)
            reading = monitor.update(obs)
            if reading.state == "ALERT":
                audio.notify()
            marker = (reading.state, reading.reason)
            if marker != previous_state:
                print(f"{t:7.2f}s  {reading.state:14} {reading.reason}")
                previous_state = marker
            if recorder:
                recorder.append(reading)
            processed += 1
            processing_fps = 1 / max(time.monotonic() - tick, 1e-6)
            if not args.headless:
                display = draw_dashboard(frame, reading, points, processing_fps)
                cv2.imshow("DrowsyGuard - prototype", display)
                # Replay wait is a responsiveness aid, not the measurement clock.
                wait = max(1, round(1000 / rate - (time.monotonic() - tick) * 1000)) if args.video else 1
                key = cv2.waitKey(min(wait, 100)) & 0xFF
                if key in (ord('q'), 27) or cv2.getWindowProperty("DrowsyGuard - prototype", cv2.WND_PROP_VISIBLE) < 1:
                    break
                if key == ord('c'):
                    monitor = Monitor(config, calibrate=True)
                if key == ord('m'):
                    audio.enabled = not audio.enabled
            if args.max_frames and processed >= args.max_frames:
                break
        if args.video and processed == 0:
            raise RuntimeError("La vidéo n'a fourni aucune image décodable")
    finally:
        if tracker:
            tracker.close()
        if cap:
            cap.release()
        cv2.destroyAllWindows()
        if recorder:
            recorder.close(config, {"processed_frames": processed,
                "processing_wall_seconds": time.monotonic() - started,
                "final_ear_threshold": monitor.threshold})
    print(f"{processed} images traitées. Aucune image de caméra enregistrée.")


def main(argv=None):
    parser = argparse.ArgumentParser(description="DrowsyGuard — prototype local de signaux de somnolence")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("download", help="Télécharger explicitement le modèle officiel")
    sub.add_parser("doctor", help="Vérifier bibliothèques et modèle sans ouvrir la caméra")
    for name in ("run", "demo"):
        command = sub.add_parser(name)
        command.add_argument("--config", help="Paramètres JSON")
        command.add_argument("--ear-threshold", type=float)
        command.add_argument("--output", help="Nouveau dossier pour CSV et rapport ; pas d'images caméra")
        command.add_argument("--headless", action="store_true")
        if name == "run":
            command.add_argument("--camera", type=int, default=0)
            command.add_argument("--video")
            command.add_argument("--max-frames", type=int, default=0)
            command.add_argument("--no-calibrate", action="store_true")
            command.add_argument("--mute", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.command == "download":
            print(download_model())
        elif args.command == "doctor":
            import cv2
            import mediapipe
            import numpy
            print(json.dumps({"opencv": cv2.__version__, "mediapipe": mediapipe.__version__,
                              "numpy": numpy.__version__, "model": str(verify_model()),
                              "camera_opened": False}, indent=2))
        elif args.command == "demo":
            demo(args, config_from_args(args))
        else:
            if args.max_frames < 0:
                raise ValueError("--max-frames doit être positif ou nul")
            run(args, config_from_args(args))
        return 0
    except (OSError, ValueError, RuntimeError, TypeError) as error:
        print(f"ERREUR : {error}")
        return 2

