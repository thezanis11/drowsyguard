"""Local display, audio and optional numeric exports (no image recording)."""
from dataclasses import asdict
from pathlib import Path
import csv
import html
import json
import threading
import time

COLORS = {"ALERT": (85, 75, 245), "WATCH": (50, 190, 255),
          "UNOBSERVABLE": (150, 150, 155), "CALIBRATING": (230, 180, 60),
          "MONITORING": (155, 215, 70)}
TITLES = {"ALERT": "ALERTE", "WATCH": "A SURVEILLER", "UNOBSERVABLE": "NON OBSERVABLE",
          "CALIBRATING": "CALIBRATION", "MONITORING": "SURVEILLANCE"}
MESSAGES = {"PROLONGED_EYE_CLOSURE": "Fermeture prolongee des yeux",
            "HIGH_CLOSED_EYE_FRACTION": "Fermetures frequentes sur la fenetre",
            "PROLONGED_MOUTH_OPENING": "Bouche ouverte : parole ou baillement possible",
            "KEEP_EYES_OPEN": "Gardez les yeux ouverts, visage face camera",
            "NO_FACE": "Aucun visage exploitable",
            "MULTIPLE_FACES": "Une seule personne attendue",
            "FACE_TOO_SMALL": "Rapprochez le visage de la camera",
            "POSE_UNRELIABLE": "Revenez face a la camera",
            "FACE_OUT_OF_FRAME": "Repositionnez le visage dans le cadre",
            "SAMPLING_GAP": "Cadence insuffisante ou capture interrompue",
            "NO_RULE_TRIGGERED": "Aucun seuil franchi ; ce n'est pas une garantie"}


class AudioAlert:
    def __init__(self, enabled=True):
        self.enabled = enabled
        self.last = -100.0
        self.thread = None

    def notify(self):
        if not self.enabled or time.monotonic() - self.last < 3:
            return
        if self.thread is not None and self.thread.is_alive():
            return
        self.last = time.monotonic()
        def beep():
            try:
                import winsound
                winsound.Beep(950, 250)
                winsound.Beep(1250, 250)
            except (ImportError, RuntimeError):
                pass  # Visual alerts remain available on every platform.
        self.thread = threading.Thread(target=beep, daemon=True)
        self.thread.start()


def draw_dashboard(frame, reading, points=(), fps=0, demo=False):
    import cv2
    import numpy as np
    canvas = np.zeros((640, 1120, 3), dtype=np.uint8)
    canvas[:] = (24, 18, 15)
    def text(s, x, y, size=.65, color=(225, 230, 235), thick=1):
        cv2.putText(canvas, s, (x, y), cv2.FONT_HERSHEY_SIMPLEX, size, color, thick, cv2.LINE_AA)
    text("DROWSYGUARD", 28, 42, 1.0, (235, 245, 250), 2)
    text("Prototype local / reconstruction 2026", 28, 70, .55, (145, 160, 175))
    color = COLORS[reading.state]
    view_w, view_h = 720, 470
    h, w = frame.shape[:2]
    scale = min(view_w / w, view_h / h)
    scaled = cv2.resize(frame, (round(w * scale), round(h * scale)))
    ox, oy = 24 + (view_w - scaled.shape[1]) // 2, 98 + (view_h - scaled.shape[0]) // 2
    canvas[oy:oy + scaled.shape[0], ox:ox + scaled.shape[1]] = scaled
    for x, y in points:
        cv2.circle(canvas, (ox + round(x * scale), oy + round(y * scale)), 2, (80, 230, 230), -1)
    cv2.rectangle(canvas, (24, 98), (744, 568), color, 3)
    text(TITLES[reading.state], 774, 126, .72, color, 2)
    for i, label in enumerate(MESSAGES.get(reading.reason, reading.reason).split(" : ")):
        # Short status lines avoid text clipping on the fixed-width panel.
        for j in range(0, len(label), 33):
            text(label[j:j + 33], 774, 154 + i * 20 + j // 33 * 20, .45, color)
    metrics = [("EAR / seuil", "--" if reading.ear is None else f"{reading.ear:.3f} / {reading.threshold:.3f}"),
               ("Yeux fermes", f"{reading.closed_seconds:.1f} s"),
               ("Fraction fermee", "--" if reading.closed_fraction is None else f"{reading.closed_fraction * 100:.1f} %"),
               ("Couverture", f"{reading.coverage * 100:.1f} %"),
               ("Bouche ouverte", f"{reading.mouth_seconds:.1f} s"),
               ("Clignements / bouche", f"{reading.blinks} / {reading.mouth_events}"),
               ("Temps / cadence", f"{reading.t:.1f} s / {fps:.1f} fps")]
    for index, (label, value) in enumerate(metrics):
        y = 230 + 43 * index
        text(label, 774, y, .47, (145, 160, 175))
        text(value, 774, y + 22, .65)
    text("Q : quitter    C : recalibrer    M : son", 28, 605, .55)
    text("DEMO SYNTHETIQUE - pas une mesure de performance" if demo else
         "Demonstration uniquement - ne pas utiliser pour conduire", 28, 630, .48, (130, 180, 240))
    return canvas


class Recorder:
    def __init__(self, directory, source):
        self.path = Path(directory)
        self.path.mkdir(parents=True, exist_ok=True)
        # Never overwrite an earlier session.
        if any((self.path / name).exists() for name in ("metrics.csv", "summary.json", "report.html")):
            raise FileExistsError("Un export existe déjà dans ce dossier ; choisissez un nouveau dossier")
        self.handle = (self.path / "metrics.csv").open("x", newline="", encoding="utf-8")
        self.writer = None
        self.rows = []
        self.events = []
        self.previous = None
        self.source = source

    def append(self, reading):
        row = asdict(reading)
        if self.writer is None:
            self.writer = csv.DictWriter(self.handle, fieldnames=list(row))
            self.writer.writeheader()
        self.writer.writerow(row)
        # Report decimation affects the chart only; CSV retains every reading.
        marker = (reading.state, reading.reason)
        if not self.rows or reading.t - self.rows[-1]["t"] >= .2 or marker != self.previous:
            self.rows.append(row)
        if marker != self.previous:
            self.events.append({"t": reading.t, "state": reading.state, "reason": reading.reason})
            self.previous = marker

    def close(self, config, extra=None):
        self.handle.close()
        summary = {"source_type": self.source, "config": asdict(config),
                   "events": self.events, "notes": [
                       "Rules are heuristic, not a clinical or driving-safety assessment.",
                       "Synthetic results test logic, not drowsiness detection accuracy.",
                       "No camera images or landmarks are stored in this export."], **(extra or {})}
        (self.path / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
        span = max((r["t"] for r in self.rows), default=1) or 1
        # Separate segments avoid visually interpolating across missing observations.
        segments, current = [], []
        previous_t = None
        for row in self.rows:
            broken = (row["ear"] is None or row["state"] == "UNOBSERVABLE"
                      or previous_t is not None and row["t"] - previous_t > config.max_gap)
            previous_t = row["t"]
            if broken:
                if current:
                    segments.append(current)
                current = []
            else:
                current.append(f'{40 + row["t"] / span * 900:.1f},{250 - row["ear"] * 450:.1f}')
        if current:
            segments.append(current)
        lines = ''.join(f'<polyline points="{" ".join(s)}" fill="none" stroke="#5ce0c0" stroke-width="2"/>' for s in segments)
        events = ''.join(f'<tr><td>{e["t"]:.2f} s</td><td>{html.escape(e["state"])}</td>'
                         f'<td>{html.escape(e["reason"])}</td></tr>' for e in self.events)
        (self.path / "report.html").write_text(f'''<!doctype html><html lang="fr"><meta charset="utf-8">
<title>DrowsyGuard — session</title><style>body{{background:#101b28;color:#e8f1f8;font:16px system-ui;margin:4vw;max-width:1100px}}h1{{color:#5ce0c0}}td,th{{padding:12px;border-bottom:1px solid #304053;text-align:left}}svg{{width:100%;background:#192838;border-radius:12px}}code{{color:#5ce0c0}}</style>
<h1>DrowsyGuard · Rapport de session</h1><p>Source : <strong>{html.escape(self.source)}</strong>.</p>
<p>Règles heuristiques d'ouverture des yeux et de la bouche. Aucun score de précision clinique ou de sécurité routière n'est calculé.</p>
<h2>Ouverture des yeux (EAR)</h2><svg viewBox="0 0 980 290" role="img" aria-label="Courbe EAR, interruptions exclues">{lines}<text x="40" y="275" fill="white">0 s</text><text x="900" y="275" fill="white">{span:.1f} s</text></svg>
<h2>Changements d'état</h2><table><thead><tr><th>Temps</th><th>État</th><th>Raison</th></tr></thead><tbody>{events}</tbody></table>
<p>Les pertes de suivi ne sont pas assimilées à des yeux ouverts. Les intervalles absents de la courbe ne sont pas interpolés. Détails numériques : <code>metrics.csv</code>, paramètres : <code>summary.json</code>.</p></html>''', encoding="utf-8")

