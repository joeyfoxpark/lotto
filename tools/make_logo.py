# -*- coding: utf-8 -*-
"""
로또리에 로고 배경 제거 + 엠블럼 추출
--------------------------------------------------
'lottorie logo.png' 의 바깥 흰 배경만 투명 처리(엠블럼 내부 흰색은 유지)하고,
 - web_static/assets/logo_full.png    : 전체 로고(투명)
 - web_static/assets/logo_emblem.png  : 상단 엠블럼(원+7+와인)만, 헤더/파비콘용
을 생성한다.
"""
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "lottorie logo.png"
OUT = ROOT / "web_static" / "assets"
OUT.mkdir(parents=True, exist_ok=True)

im = Image.open(SRC).convert("RGB")
w, h = im.size
SENTINEL = (0, 255, 0)  # 로고에 없는 색

# 네 모서리에서 근접 흰색 영역을 flood-fill (엠블럼 내부는 연결 안돼 유지됨)
for corner in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]:
    ImageDraw.floodfill(im, corner, SENTINEL, thresh=45)

# SENTINEL → 투명, 나머지 불투명
data = im.getdata()
newdata = [(0, 0, 0, 0) if p == SENTINEL else (p[0], p[1], p[2], 255) for p in data]
rgba = Image.new("RGBA", (w, h))
rgba.putdata(newdata)

# 전체 로고: 내용 bbox로 크롭
full = rgba.crop(rgba.getbbox())
full.save(OUT / "logo_full.png")

# 행별 불투명 픽셀 수로 '엠블럼 band' 찾기 (상단 연속 내용 → 첫 빈 줄까지)
alpha = rgba.split()[3]
apx = alpha.load()
row_has = []
for y in range(h):
    cnt = 0
    for x in range(0, w, 3):      # 3픽셀 간격 샘플(속도)
        if apx[x, y] > 0:
            cnt += 1
    row_has.append(cnt)

thr = 2
top = next(y for y in range(h) if row_has[y] > thr)
# top 이후 내용이 끊기는(엠블럼과 글자 사이 여백) 지점
y = top
while y < h and row_has[y] > thr:
    y += 1
emblem_bottom = y  # 엠블럼 아래 여백 시작

emblem = rgba.crop((0, top, w, emblem_bottom))
emblem = emblem.crop(emblem.getbbox())  # 좌우 여백 제거
# 여백 살짝 추가(정사각형 캔버스에 중앙 배치 → 헤더/파비콘에서 안정적)
side = max(emblem.size) + 24
canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
canvas.paste(emblem, ((side - emblem.size[0]) // 2, (side - emblem.size[1]) // 2), emblem)
canvas.save(OUT / "logo_emblem.png")
# 헤더/파비콘 임베드용 축소본 (base64 크기 절감)
canvas.resize((128, 128), Image.LANCZOS).save(OUT / "logo_header.png", optimize=True)
# 앱 아이콘용 512 (플레이스토어 대비)
canvas.resize((512, 512), Image.LANCZOS).save(OUT / "logo_icon512.png", optimize=True)

print(f"전체 로고: {full.size} -> logo_full.png")
print(f"엠블럼: {emblem.size} (캔버스 {canvas.size}) -> logo_emblem.png")
print(f"엠블럼 band: y={top}~{emblem_bottom}")
