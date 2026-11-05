#!/usr/bin/env python3
"""scene.json에 적은 자리를 그림 위에 그려 확인한다(렌더 전에 눈으로 맞추기).

    python3 scene_preview.py scene.json -o preview.png

청록 = 눈이 내리는 유리창(region) · 빨강 = 그 앞을 가리는 물건(occluders/occluder_lines)
노랑 원 = 불빛(r, sx·sy 타원) · 흰 점 = 김 나는 자리 · 격자 = 100px 눈금(좌표 읽기용)
"""
import argparse, json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FONTS = ["/System/Library/Fonts/AppleSDGothicNeo.ttc", "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
         "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc", "C:/Windows/Fonts/malgun.ttf",
         "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]


def label_font(size):
    for f in FONTS:
        if Path(f).exists():
            try:
                return ImageFont.truetype(f, size)
            except OSError:
                pass
    return ImageFont.load_default()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("scene")
    ap.add_argument("-o", "--out", default="preview.png")
    ap.add_argument("--grid", action="store_true", help="100px 눈금 + 숫자")
    a = ap.parse_args()
    sp = Path(a.scene)
    cfg = json.loads(sp.read_text())
    img = Image.open(sp.parent / cfg["image"]).convert("RGBA")
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    W, H = img.size
    ft = label_font(max(14, H // 50))
    if a.grid:
        for x in range(0, W, 100):
            d.line([(x, 0), (x, H)], fill=(255, 255, 255, 60))
            d.text((x + 3, 3), str(x), fill=(255, 255, 255, 200), font=ft)
        for y in range(0, H, 100):
            d.line([(0, y), (W, y)], fill=(255, 255, 255, 60))
            d.text((3, y + 3), str(y), fill=(255, 255, 255, 200), font=ft)
    reg = cfg.get("snow", {}).get("region")
    if reg:
        d.polygon([tuple(p) for p in reg], fill=(0, 220, 255, 40), outline=(0, 220, 255, 255))
    for poly in cfg.get("occluders", []):
        d.polygon([tuple(p) for p in poly], fill=(255, 40, 40, 110), outline=(255, 40, 40, 255))
    for x1, y1, x2, y2, w in cfg.get("occluder_lines", []):
        d.line([(x1, y1), (x2, y2)], fill=(255, 40, 40, 140), width=int(w))
    for l in cfg.get("lights", []):
        r = l.get("r", 300); sx, sy = l.get("sx", 1), l.get("sy", 1)
        x, y = l["x"], l["y"]
        d.ellipse([x - r * sx, y - r * sy, x + r * sx, y + r * sy], outline=(255, 210, 60, 230), width=3)
        d.ellipse([x - 6, y - 6, x + 6, y + 6], fill=(255, 210, 60, 255))
        if l.get("name"):
            d.text((x + 10, y - 8), l["name"], fill=(255, 230, 120, 255), font=ft)
    for s in cfg.get("steam", []):
        x, y = s["x"], s["y"]
        d.ellipse([x - 8, y - 8, x + 8, y + 8], fill=(255, 255, 255, 255))
        d.line([(x, y), (x, y - s.get("rise", 190))], fill=(255, 255, 255, 160), width=2)
    Image.alpha_composite(img, lay).convert("RGB").save(a.out)
    print(a.out, img.size)


if __name__ == "__main__":
    main()
