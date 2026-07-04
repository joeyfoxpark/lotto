# -*- coding: utf-8 -*-
"""
정적 HTML용 데이터 묶음 생성
--------------------------------------------------
lotto.db 에서 데이터를 뽑고, 음력->양력 변환 테이블을 만들어
web_static/data.json 하나로 저장한다. (index.html 에 내장됨)

내장 데이터:
  draws          : 전체 회차 [round, date, n1..n6, bonus, r1winners, r1each, sales]
  ranking        : 명당 랭킹 Top100 [name, region, address, wins]
  storesByRound  : 회차별 1등 판매점 {round: [[name, region, address, auto], ...]}
  lunar          : 음력->양력 변환용 (연도별 각 음력월 1일의 기준일 오프셋)
  lunarBaseYmd   : 오프셋 기준 양력 날짜
"""

import json
import sqlite3
from datetime import date
from pathlib import Path

from korean_lunar_calendar import KoreanLunarCalendar

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "lotto.db"
OUT = Path(__file__).resolve().parent / "data.json"

LUNAR_BASE = date(1900, 1, 1)       # 오프셋 기준일
LUNAR_YEARS = range(1930, 2027)     # 지원 범위


def get_draws(conn):
    rows = conn.execute("""
        SELECT round, date, n1,n2,n3,n4,n5,n6, bonus,
               rank1_winners, rank1_prize_each, total_sales
        FROM draws ORDER BY round
    """).fetchall()
    return [[r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[8],
             r[9] or 0, r[10] or 0, r[11] or 0] for r in rows]


def get_ranking(conn):
    rows = conn.execute("""
        SELECT name, region, MAX(address) AS addr, COUNT(*) AS wins
        FROM winning_stores WHERE rank=1 AND name IS NOT NULL
        GROUP BY COALESCE(shop_id, name || address)
        ORDER BY wins DESC, name LIMIT 100
    """).fetchall()
    return [[r[0], r[1], r[2], r[3]] for r in rows]


def get_stores_by_round(conn, rank=1, min_round=0):
    rows = conn.execute("""
        SELECT round, name, region, address, auto_type
        FROM winning_stores WHERE rank=? AND round>=? ORDER BY round, seq
    """, (rank, min_round)).fetchall()
    out = {}
    for rnd, name, region, addr, auto in rows:
        out.setdefault(rnd, []).append([name, region, addr, auto])
    return out


def get_region_stats(conn):
    """지역별 1등 배출 횟수 {지역: 횟수}."""
    rows = conn.execute("""
        SELECT region, COUNT(*) FROM winning_stores
        WHERE rank=1 AND region IS NOT NULL GROUP BY region
    """).fetchall()
    return {r[0]: r[1] for r in rows}


def get_region_top(conn, topn=3):
    """지역별 1등 최다 배출 판매점 Top3 {지역: [[상호, 횟수], ...]}."""
    rows = conn.execute("""
        SELECT region, name, COUNT(*) c FROM winning_stores
        WHERE rank=1 AND region IS NOT NULL AND name IS NOT NULL
        GROUP BY region, COALESCE(shop_id, name || address)
    """).fetchall()
    byreg = {}
    for region, name, c in rows:
        byreg.setdefault(region, []).append([name, c])
    return {reg: sorted(lst, key=lambda x: -x[1])[:topn] for reg, lst in byreg.items()}


def build_lunar_table():
    """연도별 [ [음력월, 윤달여부(0/1), 양력1일의 기준일오프셋], ... ]"""
    cal = KoreanLunarCalendar()
    table = {}
    base_ord = LUNAR_BASE.toordinal()
    for y in LUNAR_YEARS:
        months = []
        for m in range(1, 13):
            for leap in (False, True):
                ok = cal.setLunarDate(y, m, 1, leap)
                if not ok:
                    continue
                iso = cal.SolarIsoFormat()
                yy, mm, dd = map(int, iso.split("-"))
                offset = date(yy, mm, dd).toordinal() - base_ord
                months.append([m, 1 if leap else 0, offset])
        table[y] = months
    return table


def validate_lunar(table):
    """음력 1990-04-21 -> 양력 1990-05-15 인지 테이블로 재현 검증."""
    base_ord = LUNAR_BASE.toordinal()
    for m, leap, off in table[1990]:
        if m == 4 and leap == 0:
            solar = date.fromordinal(base_ord + off + (21 - 1))
            assert solar == date(1990, 5, 15), solar
            print("  음력 검증 OK: 1990-04-21 ->", solar)
            return
    raise AssertionError("음력 1990년 4월을 찾지 못함")


def main():
    conn = sqlite3.connect(DB)
    newest = conn.execute("SELECT MAX(round) FROM draws").fetchone()[0] or 0
    data = {
        "draws": get_draws(conn),
        "ranking": get_ranking(conn),
        "storesByRound": get_stores_by_round(conn, rank=1),
        "storesByRound2": get_stores_by_round(conn, rank=2, min_round=newest - 51),
        "regionStats": get_region_stats(conn),
        "regionTop": get_region_top(conn),
        "lunarBaseYmd": LUNAR_BASE.isoformat(),
        "lunar": build_lunar_table(),
    }
    conn.close()
    validate_lunar(data["lunar"])
    OUT.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")),
                   encoding="utf-8")
    size = OUT.stat().st_size
    print(f"  draws {len(data['draws'])} / ranking {len(data['ranking'])} / "
          f"storesRounds {len(data['storesByRound'])} / lunarYears {len(data['lunar'])}")
    print(f"  저장: {OUT}  ({size/1024:.0f} KB)")


if __name__ == "__main__":
    main()
