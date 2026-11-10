"""Explicit model download; subsequent uses verify the recorded hash."""
from pathlib import Path
import hashlib
import json
import shutil
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "models" / "face_landmarker.task"
MODEL_URL = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"
MANIFEST = ROOT / "models" / "provenance.json"


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def verify_model():
    if not MODEL.is_file() or not MANIFEST.is_file():
        raise FileNotFoundError("Modèle absent. Lancez Installer.bat ou python -m drowsyguard download")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if manifest.get("url") != MODEL_URL or sha256(MODEL) != manifest.get("sha256"):
        raise ValueError("L'empreinte du modèle diffère du manifeste local")
    return MODEL


def download_model():
    if MODEL.exists():
        return verify_model()
    if shutil.disk_usage(ROOT).free < 100 * 1024 * 1024:
        raise RuntimeError("Moins de 100 Mo libres : téléchargement interrompu")
    MODEL.parent.mkdir(parents=True, exist_ok=True)
    temporary = MODEL.with_suffix(".download")
    try:
        with urllib.request.urlopen(MODEL_URL, timeout=60) as response, temporary.open("wb") as out:
            total = 0
            while chunk := response.read(1024 * 1024):
                total += len(chunk)
                if total > 30 * 1024 * 1024:
                    raise ValueError("Le modèle dépasse la limite de téléchargement")
                out.write(chunk)
        if not zipfile.is_zipfile(temporary):
            raise ValueError("Le modèle reçu n'est pas un bundle MediaPipe")
        digest = sha256(temporary)
        if MANIFEST.exists():
            old = json.loads(MANIFEST.read_text(encoding="utf-8"))
            if old.get("sha256") != digest:
                raise ValueError("Empreinte différente du modèle précédemment enregistré")
        temporary.replace(MODEL)
        MANIFEST.write_text(json.dumps({"url": MODEL_URL, "sha256": digest,
            "bytes": MODEL.stat().st_size, "source": "Google MediaPipe Face Landmarker, version 1",
            "note": "Hash recorded at download; not an independent authenticity signature."}, indent=2), encoding="utf-8")
    finally:
        temporary.unlink(missing_ok=True)
    return verify_model()
