# -*- coding: utf-8 -*-
"""
원클릭 업데이트
--------------------------------------------------
새 회차 당첨번호 + 최근 판매점을 받아서 lotto.html까지 다시 만든다.
매주 토요일 추첨(밤 8시 40분경) 이후에 실행하면 최신으로 갱신된다.

실행:  python update.py     (또는 update.bat 더블클릭)
"""

import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PY = sys.executable
LOG = ROOT / "data" / "update_log.txt"


def log(msg):
    line = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
    print(line)
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def run(title, args):
    print("\n" + "=" * 56)
    print(f"▶ {title}")
    print("=" * 56)
    subprocess.run([PY] + args, cwd=str(ROOT), check=False)


def main():
    log("업데이트 시작")
    # 1) 회차 당첨번호 (증분) — 추첨 직후 바로 반영됨
    run("1/4 당첨번호 수집", ["collector/collect_lotto.py"])
    # 2) 최근 회차 판매점 (1·2등, 최신부터 소량) — 새 회차 배출점은 며칠 뒤 확정될 수 있음
    run("2/4 최근 1등 판매점", ["collector/collect_stores.py", "1", "1200", "99999"])
    run("3/4 최근 2등 판매점", ["collector/collect_stores.py", "2", "1200", "99999"])
    # 3) 데이터 묶음 + HTML 재생성
    run("4/4 웹 파일 재생성", ["web_static/build_data.py"])
    subprocess.run([PY, "web_static/build_html.py"], cwd=str(ROOT), check=False)
    # 최신 회차 기록
    try:
        import sqlite3
        n = sqlite3.connect(str(ROOT / "data" / "lotto.db")).execute(
            "SELECT MAX(round) FROM draws").fetchone()[0]
        log(f"업데이트 완료 — 최신 {n}회차")
    except Exception:
        log("업데이트 완료")
    print("\n✅ 완료! web_static/lotto.html 가 최신으로 갱신되었습니다.")


if __name__ == "__main__":
    main()
