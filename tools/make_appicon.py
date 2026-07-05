# -*- coding: utf-8 -*-
"""
안드로이드 런처 아이콘 생성 (로고 엠블럼 + 블랙 배경)
mipmap-mdpi ~ xxxhdpi 에 ic_launcher.png / ic_launcher_round.png 생성.
"""
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
EMBLEM = ROOT / "web_static" / "assets" / "logo_emblem.png"
RES = ROOT / "android" / "app" / "src" / "main" / "res"

BLACK = (16, 15, 13, 255)          # 앱 배경색과 동일
DENS = {"mdpi": 48, "hdpi": 72, "xhdpi": 96, "xxhdpi": 144, "xxxhdpi": 192}

emblem = Image.open(EMBLEM).convert("RGBA")


def make(size, round_icon):
    icon = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    # 배경(검정) — 사각(둥근모서리) 또는 원
    bg = Image.new("RGBA", (size, size), BLACK)
    mask = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(mask)
    if round_icon:
        d.ellipse([0, 0, size - 1, size - 1], fill=255)
    else:
        r = int(size * 0.22)
        d.rounded_rectangle([0, 0, size - 1, size - 1], radius=r, fill=255)
    icon.paste(bg, (0, 0), mask)
    # 엠블럼 올리기
    em = emblem.resize((int(size * 0.84), int(size * 0.84)), Image.LANCZOS)
    icon.alpha_composite(em, ((size - em.width) // 2, (size - em.height) // 2))
    return icon


for name, size in DENS.items():
    outdir = RES / f"mipmap-{name}"
    outdir.mkdir(parents=True, exist_ok=True)
    make(size, False).save(outdir / "ic_launcher.png")
    make(size, True).save(outdir / "ic_launcher_round.png")

# 플레이스토어 등록용 512 아이콘도(고해상)
(ROOT / "android" / "playstore").mkdir(parents=True, exist_ok=True)
make(512, False).save(ROOT / "android" / "playstore" / "icon512.png")
print("아이콘 생성 완료:", list(DENS.keys()), "+ playstore/icon512.png")
