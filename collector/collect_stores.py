# -*- coding: utf-8 -*-
"""
당첨 판매점(1등/2등 배출점) 수집기
--------------------------------------------------
동행복권 개편 사이트의 판매점 조회 엔드포인트를 사용해 회차별 1·2등
당첨 판매점을 수집한다. → data/lotto.db 의 winning_stores 테이블

엔드포인트:
  GET /wnprchsplcsrch/selectLtWnShp.do?srchWnShpRnk=1|2&srchLtEpsd=<회차>
  응답 JSON: data.list[] (상호/주소/전화/자동수동/좌표 등)

실행:
  python collector/collect_stores.py           # 없는 회차만 이어받기(1·2등)
  python collector/collect_stores.py 1          # 1등만
"""

import sqlite3
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "lotto.db"

BASE = "https://www.dhlottery.co.kr"
HOME = f"{BASE}/wnprchsplcsrch/home"
API = f"{BASE}/wnprchsplcsrch/selectLtWnShp.do"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")


def make_session():
    """세션 생성 + 홈 방문(쿠키 확보). 실패 시 점점 길게 재시도."""
    s = requests.Session()
    s.headers.update({
        "User-Agent": UA,
        "Accept-Language": "ko-KR,ko;q=0.9",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": HOME,
    })
    for attempt in range(5):
        try:
            s.get(HOME, headers={"User-Agent": UA}, timeout=20)
            return s
        except Exception as e:
            wait = 10 * (attempt + 1)
            print(f"  세션 생성 실패({type(e).__name__}) — {wait}초 후 재시도 {attempt+1}/5")
            time.sleep(wait)
    raise RuntimeError("동행복권 접속 불가 (일시 차단 가능). 잠시 후 다시 실행하세요.")


def fetch_stores(s, rnd, rank):
    """특정 회차/등수의 당첨 판매점 리스트. 실패 시 빈 리스트."""
    for attempt in range(3):
        try:
            r = s.get(API, params={"srchWnShpRnk": str(rank), "srchLtEpsd": str(rnd)},
                      timeout=15)
            r.raise_for_status()
            return (r.json().get("data") or {}).get("list") or []
        except Exception as e:
            print(f"    ! {rnd}회 {rank}등 실패 {attempt+1}/3: {e}")
            time.sleep(1.5)
    return []


def init_table(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS winning_stores (
            round     INTEGER,
            rank      INTEGER,
            seq       INTEGER,   -- 회차/등수 내 순번
            name      TEXT,
            tel       TEXT,
            region    TEXT,
            address   TEXT,
            auto_type TEXT,      -- 자동/수동/반자동
            shop_id   TEXT,
            lat       REAL,
            lot       REAL,
            PRIMARY KEY (round, rank, seq)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ws_shop ON winning_stores(shop_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ws_round ON winning_stores(round)")
    conn.commit()


def collected_rounds(conn, rank):
    rows = conn.execute("SELECT DISTINCT round FROM winning_stores WHERE rank=?", (rank,)).fetchall()
    return {r[0] for r in rows}


def latest_round(conn):
    row = conn.execute("SELECT MAX(round) FROM draws").fetchone()
    return row[0] or 0


def save(conn, rnd, rank, items):
    rows = []
    for i, it in enumerate(items, 1):
        rows.append((
            rnd, rank, i,
            it.get("shpNm"), it.get("shpTelno"), it.get("region"),
            (it.get("shpAddr") or "").strip(), it.get("atmtPsvYnTxt"),
            it.get("ltShpId"), it.get("shpLat"), it.get("shpLot"),
        ))
    conn.executemany("""
        INSERT OR REPLACE INTO winning_stores
        (round, rank, seq, name, tel, region, address, auto_type, shop_id, lat, lot)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)
    """, rows)
    conn.commit()


def main():
    # 사용법:
    #   python collect_stores.py                 # 1·2등 전체(없는 것만), 오름차순
    #   python collect_stores.py 1               # 1등만
    #   python collect_stores.py 1 1080 1230     # 1등, 1080~1230회 지정(최신부터)
    args = sys.argv[1:]
    rng = None
    if len(args) >= 3:
        ranks = [int(args[0])]
        rng = (int(args[1]), int(args[2]))
    else:
        ranks = [int(args[0])] if args else [1, 2]

    conn = sqlite3.connect(DB_PATH, timeout=60)   # 락 대기 60초
    conn.execute("PRAGMA journal_mode=WAL")       # 동시 읽기/쓰기 완화
    conn.execute("PRAGMA busy_timeout=60000")
    init_table(conn)
    newest = latest_round(conn)
    if not newest:
        print("먼저 collect_lotto.py 로 회차 데이터를 수집하세요.")
        return

    s = make_session()
    consec_empty = 0
    for rank in ranks:
        done = collected_rounds(conn, rank)
        if rng:
            # 지정 범위를 최신 회차부터 내려가며 수집 (이미 있는 건 건너뜀)
            todo = [r for r in range(min(rng[1], newest), rng[0] - 1, -1) if r not in done]
        else:
            todo = [r for r in range(1, newest + 1) if r not in done]
        print(f"[{rank}등] 수집 대상 {len(todo)}회차 (이미 {len(done)}회차 보유)")
        for n, rnd in enumerate(todo, 1):
            items = fetch_stores(s, rnd, rank)
            save(conn, rnd, rank, items)
            # 연속으로 빈 응답이 많으면 사이트 차단/장애로 보고 세션 재생성
            consec_empty = consec_empty + 1 if not items else 0
            if consec_empty >= 15:
                print("  연속 빈 응답 — 세션 재생성 후 60초 대기")
                time.sleep(60)
                try:
                    s = make_session()
                except RuntimeError as e:
                    print(f"  중단: {e}  (이미 받은 곳까지 저장됨. 나중에 다시 실행하면 이어받음)")
                    conn.close()
                    return
                consec_empty = 0
            if n % 50 == 0 or n == len(todo):
                print(f"  {rank}등 {n}/{len(todo)} (…{rnd}회, {len(items)}개점)")
            time.sleep(0.4)  # 정중한 간격 (차단 방지)
    total = conn.execute("SELECT COUNT(*) FROM winning_stores").fetchone()[0]
    print(f"완료! winning_stores 총 {total}행")
    conn.close()


if __name__ == "__main__":
    main()
