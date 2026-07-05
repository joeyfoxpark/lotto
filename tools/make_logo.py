# -*- coding: utf-8 -*-
"""
로또리에 로고: 배경 제거 + 고급 팔레트로 리컬러 + 엠블럼/아이콘 추출
--------------------------------------------------
 - 바깥 흰 배경만 투명 (엠블럼 내부 흰색은 유지)
 - 골드(브론즈) → 샴페인 골드, 와인(크림슨) → 버건디로 리컬러 (명암 보존)
출력(web_static/assets):
 logo_full.png, logo_emblem.png, logo_header.png(128), logo_icon512.png
"""
import colorsys
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "lottorie logo.png"
OUT = ROOT / "web_static" / "assets"
OUT.mkdir(parents=True, exist_ok=True)

# 목표 팔레트 (앱과 동일하게 사용)
GOLD = (0xD0, 0xA8, 0x5F)   # 샴페인 골드
WINE = (0x7A, 0x1F, 0x2F)   # 버건디
GH, GS, _ = colorsys.rgb_to_hsv(*[c / 255 for c in GOLD])
WH, WS, _ = colorsys.rgb_to_hsv(*[c / 255 for c in WINE])


def recolor(p):
    r, g, b, a = p
    if a == 0:
        return p
    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    if s < 0.20 and v > 0.82:      # 엠블럼 내부 흰색 → 유지
        return p
    deg = h * 360
    if 22 <= deg <= 62:            # 골드 계열 → 샴페인 골드 (약간 밝게)
        nr, ng, nb = colorsys.hsv_to_rgb(GH, GS, min(1.0, v * 1.20))
    else:                          # 와인/레드 계열 → 버건디
        nr, ng, nb = colorsys.hsv_to_rgb(WH, WS, v)
    return (int(nr * 255), int(ng * 255), int(nb * 255), a)


im = Image.open(SRC).convert("RGB")
w, h = im.size
SENTINEL = (0, 255, 0)
for corner in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]:
    ImageDraw.floodfill(im, corner, SENTINEL, thresh=45)

src = list(im.getdata())
rgba_data = [(0, 0, 0, 0) if p == SENTINEL else recolor((p[0], p[1], p[2], 255)) for p in src]
rgba = Image.new("RGBA", (w, h))
rgba.putdata(rgba_data)

# 전체 로고
full = rgba.crop(rgba.getbbox())
full.save(OUT / "logo_full.png")

# 엠블럼 band 추출 (상단 연속 내용)
alpha = rgba.split()[3]
apx = alpha.load()
row_has = [sum(1 for x in range(0, w, 3) if apx[x, y] > 0) for y in range(h)]
thr = 2
top = next(y for y in range(h) if row_has[y] > thr)
y = top
while y < h and row_has[y] > thr:
    y += 1
emblem = rgba.crop((0, top, w, y))
emblem = emblem.crop(emblem.getbbox())
side = max(emblem.size) + 24
canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
canvas.paste(emblem, ((side - emblem.size[0]) // 2, (side - emblem.size[1]) // 2), emblem)
canvas.save(OUT / "logo_emblem.png")
canvas.resize((128, 128), Image.LANCZOS).save(OUT / "logo_header.png", optimize=True)
canvas.resize((512, 512), Image.LANCZOS).save(OUT / "logo_icon512.png", optimize=True)

print(f"전체 {full.size} / 엠블럼 {emblem.size} / 골드 {GOLD} 와인 {WINE}")
