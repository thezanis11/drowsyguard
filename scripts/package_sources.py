"""Create a small source archive, excluding environments, model and face fixture."""
from pathlib import Path
import hashlib
import json
import zipfile

ROOT = Path(__file__).resolve().parents[1]
archive = ROOT.parent / "DrowsyGuard_sources_2026-11-10.zip"
allowed_roots = {"drowsyguard", "tests", "scripts", "docs", "reports", "models", ".github"}
included = []
with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as out:
    for path in sorted(ROOT.rglob("*")):
        rel = path.relative_to(ROOT)
        if not path.is_file() or ".venv" in rel.parts or "__pycache__" in rel.parts:
            continue
        if len(rel.parts) > 1 and rel.parts[0] not in allowed_roots:
            continue
        if path.suffix in {".task", ".pyc", ".download"}:
            continue
        out.write(path, "drowsyguard/" + rel.as_posix())
        included.append(rel.as_posix())
manifest = {"archive": archive.name, "bytes": archive.stat().st_size,
            "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(), "files": included,
            "excluded": [".venv", "model weights", "portrait fixture", "local video and outputs"]}
(ROOT.parent / "DrowsyGuard_archive_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
print(json.dumps({k: v for k, v in manifest.items() if k != "files"}, indent=2))
