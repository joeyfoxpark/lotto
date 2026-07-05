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
# 로컬 열람용 index.html
(HERE / "index.html").write_text(out, encoding="utf-8")
# GitHub Pages(브랜치 /docs 기반) 진입점
docs = HERE.parent / "docs"
docs.mkdir(exist_ok=True)
(docs / "index.html").write_text(out, encoding="utf-8")
(docs / ".nojekyll").write_text("", encoding="utf-8")   # Jekyll 처리 비활성화
print(f"생성 완료: {dest}  ({dest.stat().st_size/1024:.0f} KB)  (+ index.html, docs/index.html)")
