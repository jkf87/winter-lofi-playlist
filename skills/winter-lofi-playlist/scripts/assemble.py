#!/usr/bin/env python3
"""루프 영상 + 플레이리스트 음원 → 곡 제목이 뜨는 플리 영상 한 편.

    python3 assemble.py --loop loop.mp4 --mix out/ -o out/playlist.mp4
    python3 assemble.py --loop loop.mp4 --mix out/ -o out/playlist.mp4 --title-secs 12 --label "Winter Night Coding"

--mix 폴더에는 mix.py가 만든 playlist.mp3·tracklist.json이 있어야 한다.
나오는 것: playlist.mp4(루프를 음원 길이만큼 이어 붙임, 왼쪽 아래 지금 곡 제목, 처음·끝 페이드),
           thumbnail.jpg(제목 없는 장면 한 장 — 글자는 따로 얹는다)
"""
import argparse, json, subprocess, sys, tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

FONTS = [
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",
    "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "C:/Windows/Fonts/malgun.ttf",
    "C:/Windows/Fonts/segoeui.ttf",
]


def font(path, size):
    for p in ([path] if path else []) + FONTS:
        if p and Path(p).exists():
            try:
                return ImageFont.truetype(p, size)
            except OSError:
                continue
    sys.exit("글꼴을 못 찾았다 — --font로 .ttf/.otf/.ttc 경로를 주세요(한글 제목이면 한글 글꼴)")


def title_png(path, W, H, label, title, idx, n, fpath, scale):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    f_small, f_big = font(fpath, round(26 * scale)), font(fpath, round(46 * scale))
    x, y = round(72 * scale), H - round(150 * scale)
    top = f"{label}  ·  {idx:02d} / {n:02d}" if label else f"{idx:02d} / {n:02d}"
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    o = round(2 * scale)
    sd.text((x + o, y + o), top, font=f_small, fill=(0, 0, 0, 170))
    sd.text((x + o, y + round(38 * scale) + o), "♪ " + title, font=f_big, fill=(0, 0, 0, 190))
    shadow = shadow.filter(ImageFilter.GaussianBlur(4 * scale))
    d.text((x, y), top, font=f_small, fill=(255, 236, 210, 200))
    d.text((x, y + round(38 * scale)), "♪ " + title, font=f_big, fill=(255, 248, 236, 245))
    strip_top = y - round(30 * scale)                 # 제목이 있는 아래 띠만 잘라 겹친다(빠름)
    Image.alpha_composite(shadow, im).crop((0, strip_top, W, H)).save(path)
    return strip_top


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--loop", required=True)
    ap.add_argument("--mix", required=True, help="mix.py 출력 폴더")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--label", default="", help="곡 번호 앞에 붙는 작은 글씨(예: Winter Night Coding)")
    ap.add_argument("--title-secs", type=float, default=0, help="곡마다 제목을 띄울 초(0 = 곡 내내)")
    ap.add_argument("--no-titles", action="store_true")
    ap.add_argument("--font")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--preset", default="veryfast")
    ap.add_argument("--crf", type=int, default=20)
    a = ap.parse_args()

    mix = Path(a.mix)
    tl = json.loads((mix / "tracklist.json").read_text())
    total, tracks = tl["total"], tl["tracks"]
    probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                            "stream=width,height", "-of", "csv=p=0", a.loop], capture_output=True, text=True, check=True)
    W, H = map(int, probe.stdout.strip().split(","))
    scale = H / 1080
    tmp = Path(tempfile.mkdtemp(prefix="wlp_"))

    inputs = ["-stream_loop", "-1", "-i", a.loop, "-i", str(mix / "playlist.mp3")]
    fc, last = [f"[0:v]fps={a.fps}[v0]"], "v0"
    if not a.no_titles:
        x = tl.get("xfade", 0)
        for i, t in enumerate(tracks):
            png = tmp / f"t{i:02d}.png"
            top = title_png(png, W, H, a.label, t["title"], i + 1, len(tracks), a.font, scale)
            st = t["start"] + (0.5 if i == 0 else x / 2)
            en = min(t["end"] - x / 2, total - 1.0) if i < len(tracks) - 1 else total - 3.0
            if a.title_secs > 0:
                en = min(en, st + a.title_secs)
            fd = min(1.2, (en - st) / 3)
            # 제목 그림은 보이는 구간만큼만 만들고 그 시각으로 민다
            inputs += ["-loop", "1", "-framerate", str(a.fps), "-t", f"{en - st:.3f}", "-i", str(png)]
            k = 2 + i  # 이 제목 그림의 입력 번호(0 루프, 1 음원)
            fc.append(f"[{k}:v]format=rgba,fade=in:st=0:d={fd:.3f}:alpha=1,"
                      f"fade=out:st={en - st - fd:.3f}:d={fd:.3f}:alpha=1,setpts=PTS+{st:.3f}/TB[t{i}]")
            fc.append(f"[{last}][t{i}]overlay=0:{top}:eof_action=pass:format=auto[v{i + 1}]")
            last = f"v{i + 1}"
    fc.append(f"[{last}]fade=in:st=0:d=2,fade=out:st={total - 3:.3f}:d=3,format=yuv420p[v]")
    fc.append(f"[1:a]afade=in:st=0:d=2,afade=out:st={total - 4:.3f}:d=4[a]")
    out = Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)
    # 썸네일용 장면(제목 없음)은 긴 인코딩 전에 먼저 뽑는다
    ldur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", a.loop],
                                capture_output=True, text=True, check=True).stdout)
    thumb = out.parent / "thumbnail.jpg"
    subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-ss", f"{min(5.0, ldur / 2):.3f}", "-i", a.loop,
                    "-frames:v", "1", "-q:v", "2", str(thumb)], check=True)
    cmd = ["ffmpeg", "-nostdin", "-loglevel", "error", "-y", *inputs, "-filter_complex", ";".join(fc),
           "-map", "[v]", "-map", "[a]", "-t", f"{total:.3f}", "-c:v", "libx264", "-preset", a.preset,
           "-crf", str(a.crf), "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out)]
    subprocess.run(cmd, check=True)
    print(json.dumps({"video": str(out), "thumbnail": str(thumb), "seconds": total, "tracks": len(tracks)},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
