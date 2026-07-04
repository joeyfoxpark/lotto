# -*- coding: utf-8 -*-
"""
동행복권 로또 6/45 당첨번호 수집기
--------------------------------------------------
1회차부터 최신 회차까지 모든 당첨번호를 수집해서
 - data/lotto.db   (SQLite 데이터베이스)
 - data/lotto.json (앱/분석에서 바로 쓰기 좋은 JSON)
두 가지 형태로 저장합니다.

동행복권 사이트가 2026년 개편되면서 예전 getLottoNumber API가 막혔고,
현재는 아래의 새 내부 엔드포인트를 사용합니다.
  GET /lt645/selectPstLt645InfoNew.do?srchDir=...&srchLtEpsd=...&srchCursorLtEpsd=...
이 엔드포인트는 한 번에 10회차씩(윈도우) JSON으로 돌려줍니다.

실행 방법 (프로젝트 폴더에서):
  python collector/collect_lotto.py
처음엔 전체를 받고, 다음부터는 새로 추가된 회차만 이어서 받습니다(증분 수집).
"""

import json
import sqlite3
import time
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
# 경로 설정: 이 파일 기준으로 프로젝트 루트/데이터 폴더를 계산 (어디서 실행해도 동작)
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "lotto.db"
JSON_PATH = DATA_DIR / "lotto.json"

# ---------------------------------------------------------------------------
# 동행복권 접근 설정
# ---------------------------------------------------------------------------
BASE = "https://www.dhlottery.co.kr"
RESULT_PAGE = f"{BASE}/lt645/result"
API = f"{BASE}/lt645/selectPstLt645InfoNew.do"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")


def make_session() -> requests.Session:
    """세션을 만들고 결과 페이지를 한 번 방문해 쿠키를 확보한다."""
    s = requests.Session()
    s.headers.update({
        "User-Agent": UA,
        "Accept-Language": "ko-KR,ko;q=0.9",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": RESULT_PAGE,
    })
    # 결과 페이지 방문 -> DHJSESSIONID / WMONID 쿠키 확보
    s.get(RESULT_PAGE, headers={"User-Agent": UA}, timeout=15)
    return s


def call_api(s: requests.Session, **params) -> list:
    """엔드포인트를 호출해 회차 리스트(list)를 돌려준다. 실패 시 빈 리스트."""
    for attempt in range(3):
        try:
            r = s.get(API, params=params, timeout=15)
            r.raise_for_status()
            body = r.json()
            return (body.get("data") or {}).get("list") or []
        except Exception as e:  # 네트워크/JSON 오류 시 잠깐 쉬고 재시도
            print(f"    ! 요청 실패({params}) {attempt+1}/3: {e}")
            time.sleep(1.5)
    return []


def normalize(rec: dict) -> dict:
    """동행복권 원본 레코드를 우리가 쓰기 좋은 형태로 정리한다."""
    ymd = str(rec.get("ltRflYmd", ""))
    date = f"{ymd[0:4]}-{ymd[4:6]}-{ymd[6:8]}" if len(ymd) == 8 else ymd
    nums = [rec.get(f"tm{i}WnNo") for i in range(1, 7)]
    return {
        "round": rec["ltEpsd"],
        "date": date,
        "numbers": nums,                     # 당첨번호 6개 (오름차순 보정)
        "bonus": rec.get("bnsWnNo"),         # 보너스 번호
        "rank1_winners": rec.get("rnk1WnNope"),      # 1등 당첨자 수
        "rank1_prize_each": rec.get("rnk1WnAmt"),    # 1등 1인당 당첨금
        "rank1_prize_total": rec.get("rnk1SumWnAmt"),# 1등 총 당첨금
        "rank2_winners": rec.get("rnk2WnNope"),
        "rank2_prize_each": rec.get("rnk2WnAmt"),
        "total_winners": rec.get("sumWnNope"),       # 전체 당첨자 수
        "total_sales": rec.get("rlvtEpsdSumNtslAmt"),# 해당 회차 총 판매액
    }


def fetch_all(s: requests.Session, start_after: int = 0) -> dict:
    """start_after 회차 다음부터 최신까지 모두 받아 {round: record} 로 반환."""
    collected = {}

    # 1회차는 latest 페이징으로 못 잡으므로(2회차부터 나옴) center로 따로 받는다.
    if start_after < 1:
        for rec in call_api(s, srchDir="center", srchLtEpsd="1"):
            collected[rec["ltEpsd"]] = rec

    # latest 방향으로 cursor를 올려가며 10회차씩 끝까지 수집
    cursor = max(start_after, 1)
    while True:
        chunk = call_api(s, srchDir="latest", srchCursorLtEpsd=str(cursor))
        if not chunk:
            break
        for rec in chunk:
            collected[rec["ltEpsd"]] = rec
        new_cursor = max(rec["ltEpsd"] for rec in chunk)
        if new_cursor <= cursor:  # 더 이상 진전 없으면 종료
            break
        cursor = new_cursor
        print(f"  ... {cursor}회차까지 수집")
        time.sleep(0.25)  # 서버 부담을 줄이기 위한 예의상 딜레이

    return collected


# ---------------------------------------------------------------------------
# 저장: SQLite
# ---------------------------------------------------------------------------
def init_db(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS draws (
            round             INTEGER PRIMARY KEY,
            date              TEXT,
            n1 INTEGER, n2 INTEGER, n3 INTEGER,
            n4 INTEGER, n5 INTEGER, n6 INTEGER,
            bonus             INTEGER,
            rank1_winners     INTEGER,
            rank1_prize_each  INTEGER,
            rank1_prize_total INTEGER,
            rank2_winners     INTEGER,
            rank2_prize_each  INTEGER,
            total_winners     INTEGER,
            total_sales       INTEGER
        )
    """)
    conn.commit()


def save_db(conn: sqlite3.Connection, rows: list) -> None:
    conn.executemany("""
        INSERT OR REPLACE INTO draws
        (round, date, n1, n2, n3, n4, n5, n6, bonus,
         rank1_winners, rank1_prize_each, rank1_prize_total,
         rank2_winners, rank2_prize_each, total_winners, total_sales)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, [(
        r["round"], r["date"], *sorted(r["numbers"]), r["bonus"],
        r["rank1_winners"], r["rank1_prize_each"], r["rank1_prize_total"],
        r["rank2_winners"], r["rank2_prize_each"], r["total_winners"], r["total_sales"],
    ) for r in rows])
    conn.commit()


def export_json(conn: sqlite3.Connection) -> int:
    """DB 전체를 회차 오름차순 JSON으로 내보낸다."""
    cur = conn.execute("SELECT * FROM draws ORDER BY round")
    cols = [c[0] for c in cur.description]
    out = []
    for row in cur.fetchall():
        d = dict(zip(cols, row))
        d["numbers"] = [d.pop("n1"), d.pop("n2"), d.pop("n3"),
                        d.pop("n4"), d.pop("n5"), d.pop("n6")]
        out.append(d)
    JSON_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return len(out)


def latest_saved_round(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT MAX(round) FROM draws").fetchone()
    return row[0] or 0


def main() -> None:
    print("동행복권 로또 6/45 수집기 시작")
    conn = sqlite3.connect(DB_PATH)
    init_db(conn)

    have = latest_saved_round(conn)
    if have:
        print(f"기존 데이터: {have}회차까지 있음 -> 다음 회차부터 이어받기")
    else:
        print("기존 데이터 없음 -> 1회차부터 전체 수집")

    s = make_session()
    collected = fetch_all(s, start_after=have)

    if not collected:
        print("새로 받은 회차가 없습니다. (이미 최신이거나 사이트 점검 중)")
        conn.close()
        return

    rows = [normalize(rec) for rec in collected.values()]
    save_db(conn, rows)
    total = export_json(conn)

    lo = min(r["round"] for r in rows)
    hi = max(r["round"] for r in rows)
    print(f"신규/갱신 {len(rows)}회차 저장 (이번 범위 {lo}~{hi})")
    print(f"전체 {total}회차 -> {DB_PATH}")
    print(f"                -> {JSON_PATH}")
    conn.close()
    print("완료!")


if __name__ == "__main__":
    main()
