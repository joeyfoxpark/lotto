# -*- coding: utf-8 -*-
"""
data.json 을 템플릿에 주입해 단일 자기포함 HTML(lotto.html) 생성.
실행: python web_static/build_html.py

출력:
  web_static/lotto.html, web_static/index.html   로컬 열람용
  docs/index.html, docs/privacy.html             GitHub Pages(브랜치 /docs) 배포용
  android/app/src/main/assets/index.html 등       앱 동봉(오프라인 실행)용 — git 미추적, CI가 docs/에서 복사
빌드 스탬프: <meta name="lottorie-build" content="UTC시각|최신회차">  (앱이 Pages의 최신본과 비교해 자동 갱신)
"""
import base64
import json
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
data = (HERE / "data.json").read_text(encoding="utf-8")
tpl = (HERE / "lotto_template.html").read_text(encoding="utf-8")

marker = "const DATA = null; /*__DATA__*/"
assert marker in tpl, "템플릿에 주입 마커가 없습니다"
out = tpl.replace(marker, f"const DATA = {data};")

# 로고(엠블럼) 이미지를 base64로 내장 (자기포함 유지, Pillow 불필요)
logo_b64 = base64.b64encode((HERE / "assets" / "logo_header.png").read_bytes()).decode()
out = out.replace("__LOGO__", f"data:image/png;base64,{logo_b64}")

# 빌드 스탬프 (UTC 시각 | 최신 회차) — 앱의 자동 갱신 비교 기준
latest_round = json.loads(data)["draws"][-1][0]
stamp = f"{datetime.now(timezone.utc):%Y%m%d%H%M%S}|{latest_round}"
assert "__BUILD__" in out, "템플릿에 빌드 스탬프 마커가 없습니다"
out = out.replace("__BUILD__", stamp)

privacy = (HERE / "privacy.html").read_text(encoding="utf-8")

dest = HERE / "lotto.html"
dest.write_text(out, encoding="utf-8")
# 로컬 열람용 index.html
(HERE / "index.html").write_text(out, encoding="utf-8")
# GitHub Pages(브랜치 /docs 기반) 진입점
docs = HERE.parent / "docs"
docs.mkdir(exist_ok=True)
(docs / "index.html").write_text(out, encoding="utf-8")
(docs / ".nojekyll").write_text("", encoding="utf-8")   # Jekyll 처리 비활성화
(docs / "privacy.html").write_text(privacy, encoding="utf-8")
# 안드로이드 앱 동봉본 (오프라인에서도 즉시 실행; 온라인이면 앱이 Pages 최신본으로 자체 갱신)
assets = HERE.parent / "android" / "app" / "src" / "main" / "assets"
assets.mkdir(parents=True, exist_ok=True)
(assets / "index.html").write_text(out, encoding="utf-8")
(assets / "privacy.html").write_text(privacy, encoding="utf-8")
print(f"생성 완료: {dest}  ({dest.stat().st_size/1024:.0f} KB)  빌드 {stamp}  (+ index.html, docs/, android assets/)")
