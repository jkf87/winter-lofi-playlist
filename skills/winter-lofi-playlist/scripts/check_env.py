#!/usr/bin/env python3
"""이 스킬이 쓰는 도구가 다 있는지 본다. 없으면 설치 방법을 알려 준다."""
import importlib, json, shutil, subprocess, sys

ok, rows = True, []


def row(name, good, how=""):
    global ok
    rows.append(("OK " if good else "NO ") + name + ("" if good else f"  → {how}"))
    if not good and not name.startswith("(선택)"):
        ok = False


row("Python 3.9+", sys.version_info >= (3, 9), "python.org")
for mod, pip in (("numpy", "numpy"), ("PIL", "Pillow")):
    try:
        importlib.import_module(mod); row(pip, True)
    except ImportError:
        row(pip, False, f"python3 -m pip install {pip}")
for b in ("ffmpeg", "ffprobe"):
    row(b, bool(shutil.which(b)), "brew install ffmpeg / apt install ffmpeg / winget install ffmpeg")
if shutil.which("ffmpeg"):
    f = subprocess.run(["ffmpeg", "-hide_banner", "-filters"], capture_output=True, text=True).stdout
    for flt in ("acrossfade", "loudnorm"):
        row(f"ffmpeg 필터 {flt}", flt in f, "ffmpeg를 새 버전으로")
    e = subprocess.run(["ffmpeg", "-hide_banner", "-encoders"], capture_output=True, text=True).stdout
    for enc in ("libx264", "libmp3lame"):
        row(f"ffmpeg 인코더 {enc}", enc in e, "libx264·libmp3lame이 든 ffmpeg 빌드")
row("(선택) codex CLI — 배경 그림 생성", bool(shutil.which("codex")),
    "npm i -g @openai/codex, 없으면 직접 준비한 그림을 쓴다")
print("\n".join(rows))
print(json.dumps({"ready": ok}))
sys.exit(0 if ok else 1)
