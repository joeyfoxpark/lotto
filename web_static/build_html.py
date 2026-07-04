# -*- coding: utf-8 -*-
"""
data.json 을 템플릿에 주입해 단일 자기포함 HTML(lotto.html) 생성.
실행: python web_static/build_html.py
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent
data = (HERE / "data.json").read_text(encoding="utf-8")
tpl = (HERE / "lotto_template.html").read_text(encoding="utf-8")

marker = "const DATA = null; /*__DATA__*/"
assert marker in tpl, "템플릿에 주입 마커가 없습니다"
out = tpl.replace(marker, f"const DATA = {data};")

dest = HERE / "lotto.html"
dest.write_text(out, encoding="utf-8")
# GitHub Pages 진입점용 index.html 도 동일하게 생성
(HERE / "index.html").write_text(out, encoding="utf-8")
print(f"생성 완료: {dest}  ({dest.stat().st_size/1024:.0f} KB)  (+ index.html)")
