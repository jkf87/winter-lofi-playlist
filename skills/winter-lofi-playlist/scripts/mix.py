#!/usr/bin/env python3
"""곡 파일들을 순서대로 크로스페이드로 이어 플레이리스트 한 파일 + 곡 시작 시각표를 만든다.

    python3 mix.py tracks/01_Snowfall_Terminal.mp3 tracks/02_Frosted_Window.mp3 ... -o out/
    python3 mix.py tracks/*.mp3 -o out/ --xfade 3 --lufs -14 --titles titles.txt

나오는 것(out/):
  playlist.mp3       크로스페이드 + 음량 맞춤(기본 -14 LUFS, 유튜브 기준)
  tracklist.json     곡마다 title·file·start·end(초) — assemble.py가 읽는다
  timestamps.txt     설명란에 붙일 「00:00 곡 제목」 목록
곡 제목은 --titles(한 줄에 하나) 또는 파일 이름(앞 번호·밑줄 제거)에서 가져온다.
"""
import argparse, json, re, subprocess, sys
from pathlib import Path


def dur(p):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                         capture_output=True, text=True, check=True).stdout
    return float(out)


def hms(s):
    s = int(round(s))
    return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}" if s >= 3600 else f"{s // 60:02d}:{s % 60:02d}"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tracks", nargs="+")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--xfade", type=float, default=3.0, help="곡 사이 크로스페이드 초(기본 3)")
    ap.add_argument("--lufs", type=float, default=-14.0, help="통합 음량 목표(기본 -14)")
    ap.add_argument("--titles", help="곡 제목 파일(한 줄에 하나, 곡 순서대로)")
    a = ap.parse_args()

    files = [Path(t) for t in a.tracks]
    for f in files:
        if not f.exists():
            sys.exit(f"없는 파일: {f}")
    if a.titles:
        titles = [l.strip() for l in Path(a.titles).read_text().splitlines() if l.strip()]
        if len(titles) != len(files):
            sys.exit(f"제목 {len(titles)}개, 곡 {len(files)}개 — 수가 다르다")
    else:
        titles = [re.sub(r"^\d+[_\-. ]*", "", f.stem).replace("_", " ").strip() for f in files]

    durs = [dur(f) for f in files]
    x = a.xfade if len(files) > 1 else 0
    if x and min(durs) <= 2 * x:
        sys.exit("크로스페이드가 곡 길이에 비해 너무 길다")
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)

    inputs = sum((["-i", str(f)] for f in files), [])
    if len(files) == 1:
        chain, last = "[0:a]anull[m]", "m"
    else:
        parts, prev = [], "0:a"
        for i in range(1, len(files)):
            lab = f"x{i}"
            parts.append(f"[{prev}][{i}:a]acrossfade=d={x}:c1=tri:c2=tri[{lab}]")
            prev = lab
        chain, last = ";".join(parts), prev
    chain += f";[{last}]loudnorm=I={a.lufs}:TP=-1.5:LRA=11,aresample=48000[out]"
    mp3 = out / "playlist.mp3"
    subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", *inputs, "-filter_complex", chain,
                    "-map", "[out]", "-c:a", "libmp3lame", "-b:a", "192k", str(mp3)], check=True)

    rows, t = [], 0.0
    for f, ti, d in zip(files, titles, durs):
        rows.append({"title": ti, "file": str(f), "start": round(t, 3), "end": round(t + d, 3)})
        t += d - x
    total = dur(mp3)
    (out / "tracklist.json").write_text(json.dumps({"xfade": x, "total": round(total, 3), "tracks": rows},
                                                   ensure_ascii=False, indent=1))
    (out / "timestamps.txt").write_text("".join(f"{hms(r['start'])} {r['title']}\n" for r in rows))
    print(json.dumps({"playlist": str(mp3), "total": hms(total), "tracks": len(rows)}, ensure_ascii=False))
    print((out / "timestamps.txt").read_text(), end="")


if __name__ == "__main__":
    main()
