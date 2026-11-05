#!/usr/bin/env python3
"""사진 한 장 + scene.json → 이음새 없는 겨울밤 루프 영상(눈·불빛 흔들림·김·카메라 숨쉬기).

모든 움직임은 루프 길이 D 안에서 정수 번 되풀이되도록 만든다. 그래서 t=0 프레임과 t=D 프레임이 같고,
루프를 몇 번 이어 붙여도 끊김이 없다.

    python3 render_loop.py scene.json -o loop.mp4            # 30초, 1920x1080, 30fps
    python3 render_loop.py scene.json --check -o check/      # 정지 화면 3장 + 이음새 검사만

필요: Python 3.9+, numpy, Pillow, ffmpeg
"""
import argparse, json, math, random, subprocess, sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

TAU = math.pi * 2


def smooth(e0, e1, x):
    u = min(1.0, max(0.0, (x - e0) / (e1 - e0)))
    return u * u * (3 - 2 * u)


def radial(size, stops):
    """반지름 0→1 구간을 stops [(위치, 값)]로 잇는 둥근 알파 스프라이트."""
    c = (size - 1) / 2
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
    d = np.sqrt((xx - c) ** 2 + (yy - c) ** 2) / max(c, 1e-6)
    pos, val = zip(*stops)
    return np.interp(d, pos, val).astype(np.float32)


class Scene:
    def __init__(self, path, W, H, D):
        self.path = Path(path)
        cfg = json.loads(self.path.read_text())
        self.cfg, self.W, self.H, self.D = cfg, W, H, D
        img = Image.open(self.path.parent / cfg["image"]).convert("RGB")
        iw, ih = img.size
        s = max(W / iw, H / ih)                       # cover 맞춤
        self.s, self.ox, self.oy = s, (iw * s - W) / 2, (ih * s - H) / 2
        img = img.resize((round(iw * s), round(ih * s)), Image.LANCZOS)
        img = img.crop((round(self.ox), round(self.oy), round(self.ox) + W, round(self.oy) + H))
        self.base = np.asarray(img, dtype=np.float32) / 255.0
        self.k = H / 1080                             # 크기 기준(1080p = 1)
        self._snow_setup(cfg.get("snow", {}))
        self._lights_setup(cfg.get("lights", []))
        self._steam_setup(cfg.get("steam", []))
        cam = cfg.get("camera", {})
        self.zoom = max(1.0, float(cam.get("zoom", 1.035)) or 1.0)   # 1 = 고정, 1보다 작으면 1로
        self.drift = float(cam.get("drift", 14)) * self.k
        self.origin = cam.get("origin", [0.56, 0.58])

    def P(self, x, y):
        return (x * self.s - self.ox, y * self.s - self.oy)

    # ---------- 눈 ----------
    def _snow_setup(self, sn):
        W, H, k = self.W, self.H, self.k
        self.snow_on = bool(sn.get("region"))
        if not self.snow_on:
            return
        region = [self.P(*p) for p in sn["region"]]
        m = Image.new("L", (W, H), 0)
        dr = ImageDraw.Draw(m)
        dr.polygon(region, fill=255)
        for poly in self.cfg.get("occluders", []):
            dr.polygon([self.P(*p) for p in poly], fill=0)
        for x1, y1, x2, y2, w in self.cfg.get("occluder_lines", []):
            dr.line([self.P(x1, y1), self.P(x2, y2)], fill=0, width=max(1, round(w * self.s)), joint="curve")
            for (x, y) in (self.P(x1, y1), self.P(x2, y2)):
                r = w * self.s / 2
                dr.ellipse([x - r, y - r, x + r, y + r], fill=0)
        m = m.filter(ImageFilter.GaussianBlur(1.5 * k))
        self.snow_mask = np.asarray(m, dtype=np.float32) / 255.0

        xs, ys = [p[0] for p in region], [p[1] for p in region]
        x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
        self.sill = sn.get("fade_bottom", True)
        self.y1 = y1
        self.loop_h = (y1 - y0) + 120 * k
        self.top = y0 - 60 * k
        rnd = random.Random(int(sn.get("seed", 1105)))
        n = round(float(sn.get("count", 460)))
        speed = max(1, round(float(sn.get("speed", 1))))
        size = float(sn.get("size", 1.0))
        self.flakes = []
        for _ in range(n):
            d = rnd.random() ** 1.6                     # 0 먼 눈 … 1 가까운 눈
            self.flakes.append(dict(
                x0=x0 - 40 * k + rnd.random() * (x1 - x0 + 80 * k),
                y0=rnd.random() * self.loop_h,
                d=d,
                r=(1.1 + d * d * 4.6) * k * size,
                kk=max(2, round((2 + d * 5) * speed)),  # 루프 동안 몇 바퀴 떨어지나(정수)
                amp=(8 + rnd.random() * 34) * k,
                f=2 + int(rnd.random() * 4),            # 흔들림 주기(정수)
                ph=rnd.random() * TAU,
                a=0.35 + d * 0.55,
            ))
        self.flakes.sort(key=lambda f: f["d"])
        self.sprites = {}
        lit = [l for l in self.cfg.get("lights", []) if l.get("lights_snow")]
        self.snow_lights = [(*self.P(l["x"], l["y"]), 300 * k) for l in lit]
        col = sn.get("color", [255, 252, 248])
        self.snow_col = np.array(col, dtype=np.float32) / 255.0

    def _sprite(self, px):
        if px not in self.sprites:
            self.sprites[px] = radial(px, [(0, 1), (0.35, 0.85), (1, 0), (9, 0)])
        return self.sprites[px]

    def snow_alpha(self, t):
        W, H, D = self.W, self.H, self.D
        A = np.zeros((H, W), dtype=np.float32)
        for f in self.flakes:
            y = self.top + ((f["y0"] + f["kk"] * self.loop_h * t / D) % self.loop_h)
            x = f["x0"] + f["amp"] * math.sin(TAU * (f["f"] * t / D) + f["ph"])
            lit = sum(math.exp(-((x - lx) ** 2 + (y - ly) ** 2) / (2 * r * r)) for lx, ly, r in self.snow_lights)
            fade = 1 - smooth(self.y1 - 135 * self.k, self.y1, y) * (0.4 + 0.6 * (1 - f["d"])) if self.sill else 1
            if self.snow_lights:  # 가로등 불빛 안의 눈은 더 밝게
                a = min(1.0, f["a"] * (0.75 + 0.9 * min(lit, 1.0))) * fade
            else:
                a = f["a"] * fade
            if a <= 0.01:
                continue
            px = max(3, int(round(f["r"] * 2.4)) | 1)
            spr = self._sprite(px)
            cx, cy = int(round(x)) - px // 2, int(round(y)) - px // 2
            sx0, sy0 = max(0, -cx), max(0, -cy)
            dx0, dy0 = max(0, cx), max(0, cy)
            dx1, dy1 = min(W, cx + px), min(H, cy + px)
            if dx1 <= dx0 or dy1 <= dy0:
                continue
            s = spr[sy0:sy0 + dy1 - dy0, sx0:sx0 + dx1 - dx0] * a
            sl = A[dy0:dy1, dx0:dx1]
            sl += s * (1 - sl)
        return A * self.snow_mask

    # ---------- 불빛 ----------
    def _lights_setup(self, lights):
        # 빛은 낮은 해상도로 계산해 올린다(넓고 부드러워 차이가 안 보인다).
        q = 4
        w, h = self.W // q, self.H // q
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        xx = (xx + 0.5) * q
        yy = (yy + 0.5) * q
        self.lights = []
        for l in lights:
            cx, cy = self.P(l["x"], l["y"])
            r = float(l.get("r", 300)) * self.s
            sx, sy = float(l.get("sx", 1)), float(l.get("sy", 1))
            d = np.sqrt(((xx - cx) / sx) ** 2 + ((yy - cy) / sy) ** 2) / r
            alpha = float(l.get("alpha", 0.15))
            g = np.interp(d, [0, 0.45, 1, 99], [alpha, alpha * 0.38, 0, 0]).astype(np.float32)
            col = np.array(l.get("color", [255, 176, 84]), dtype=np.float32) / 255.0
            fl = l.get("flicker", {})
            waves = [(max(1, round(c)), ph, wt) for c, ph, wt in fl.get("waves", [[7, 0.8, 1], [13, 2.1, 0.6]])]
            self.lights.append((g[..., None] * col, float(fl.get("amount", 0.05)), waves))
        self.flicker_scale = float(self.cfg.get("flicker", 1.0))
        self.lq = (w, h)

    def light_screen(self, t):
        """화면(screen) 합성용 (1 - Π(1 - g·k)) 지도, 출력 해상도."""
        if not self.lights:
            return None
        w, h = self.lq
        prod = np.ones((h, w, 3), dtype=np.float32)
        for g, amt, waves in self.lights:
            kf = 1 + self.flicker_scale * amt * sum(wt * math.sin(TAU * c * t / self.D + ph) for c, ph, wt in waves)
            prod *= 1 - np.clip(g * kf, 0, 1)
        up = [np.asarray(Image.fromarray(prod[..., i], "F").resize((self.W, self.H), Image.BILINEAR)) for i in range(3)]
        return 1 - np.stack(up, axis=-1)

    # ---------- 김 ----------
    def _steam_setup(self, steam):
        self.steam = []
        for s in steam:
            self.steam.append(dict(xy=self.P(s["x"], s["y"]), amount=float(s.get("amount", 1.0)),
                                   rise=float(s.get("rise", 190)) * self.s, puffs=int(s.get("puffs", 7)),
                                   cycles=max(1, round(s.get("cycles", 6)))))
        self.steam_spr = {}
        self.steam_col = np.array([1.0, 240 / 255, 225 / 255], dtype=np.float32)

    def _steam_sprite(self, px):
        if px not in self.steam_spr:
            self.steam_spr[px] = radial(px, [(0, 0.5), (0.5, 0.18), (1, 0), (9, 0)])
        return self.steam_spr[px]

    def draw_steam(self, out, t):
        W, H, k = self.W, self.H, self.k
        for s in self.steam:
            mx, my = s["xy"]
            for i in range(s["puffs"]):
                u = ((t * s["cycles"] / self.D) + i / s["puffs"]) % 1
                x = mx + 26 * k * math.sin(TAU * (u * 1.3 + i * 0.37)) + u * 14 * k
                y = my - u * s["rise"]
                r = (26 + u * 70) * k
                a = s["amount"] * 0.55 * math.sin(math.pi * min(1, u * 1.05)) * (1 - u * 0.35)
                if a <= 0.005:
                    continue
                px = max(3, int(round(r * 2)) | 1)
                spr = self._steam_sprite(px) * a
                cx, cy = int(round(x)) - px // 2, int(round(y)) - px // 2
                sx0, sy0 = max(0, -cx), max(0, -cy)
                dx0, dy0, dx1, dy1 = max(0, cx), max(0, cy), min(W, cx + px), min(H, cy + px)
                if dx1 <= dx0 or dy1 <= dy0:
                    continue
                al = spr[sy0:sy0 + dy1 - dy0, sx0:sx0 + dx1 - dx0][..., None]
                sl = out[dy0:dy1, dx0:dx1]
                sl[:] = sl * (1 - al) + self.steam_col * al

    # ---------- 한 프레임 ----------
    def frame(self, t):
        out = self.base.copy()
        if self.snow_on:
            A = self.snow_alpha(t)[..., None]
            out = out * (1 - A) + self.snow_col * A
        L = self.light_screen(t)
        if L is not None:
            out = 1 - (1 - out) * (1 - L)
        self.draw_steam(out, t)
        im = Image.fromarray((np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8))
        # 카메라 숨쉬기: 0 → 반 → 0, 처음과 끝이 정지 상태라 루프가 맞물린다
        e = (1 - math.cos(TAU * t / self.D)) / 2
        z = 1 + (self.zoom - 1) * e
        if z != 1 or self.drift:
            ox, oy = self.origin[0] * self.W, self.origin[1] * self.H
            tx, ty = -self.drift * e, -self.drift * 0.4 * e
            # 출력 좌표 p → 원본 좌표 (p - o - t)/z + o
            a, c = 1 / z, ox - (ox + tx) / z
            b, d = 1 / z, oy - (oy + ty) / z
            im = im.transform(im.size, Image.AFFINE, (a, 0, c, 0, b, d), resample=Image.BILINEAR)
        return im


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("scene")
    ap.add_argument("-o", "--out", required=True, help="loop.mp4 (또는 --check면 폴더)")
    ap.add_argument("--seconds", type=float, default=30)
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--size", default="1920x1080")
    ap.add_argument("--check", action="store_true", help="정지 화면 0·D/3·D/2 + 이음새 차이만")
    ap.add_argument("--crf", type=int, default=18)
    a = ap.parse_args()
    W, H = map(int, a.size.lower().split("x"))
    if abs(a.seconds * a.fps - round(a.seconds * a.fps)) > 1e-6:
        sys.exit("seconds × fps가 정수여야 루프 길이가 맞는다(예: 30초 × 30fps)")
    sc = Scene(a.scene, W, H, a.seconds)

    if a.check:
        out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
        for t in (0, a.seconds / 3, a.seconds / 2):
            sc.frame(t).save(out / f"still_{t:05.1f}s.png")
        f0 = np.asarray(sc.frame(0), dtype=np.int16)
        fD = np.asarray(sc.frame(a.seconds), dtype=np.int16)
        f1 = np.asarray(sc.frame(1 / a.fps), dtype=np.int16)
        seam, step = float(np.abs(f0 - fD).mean()), float(np.abs(f0 - f1).mean())
        print(json.dumps({"stills": str(out), "seam_diff": round(seam, 3), "one_frame_diff": round(step, 3),
                          "seam_ok": seam < 0.05}, ensure_ascii=False))
        return

    n = round(a.seconds * a.fps)
    cmd = ["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{W}x{H}", "-r", str(a.fps), "-i", "-", "-c:v", "libx264", "-preset", "medium",
           "-crf", str(a.crf), "-x264-params", f"keyint={n}:min-keyint={n}", "-pix_fmt", "yuv420p", "-movflags", "+faststart", a.out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(n):
        p.stdin.write(sc.frame(i / a.fps).tobytes())
        if i % (a.fps * 5) == 0:
            print(f"  {i}/{n} 프레임", file=sys.stderr, flush=True)
    p.stdin.close()
    if p.wait():
        sys.exit("ffmpeg 실패")
    print(json.dumps({"loop": a.out, "seconds": a.seconds, "frames": n, "size": f"{W}x{H}"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
