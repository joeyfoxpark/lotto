# -*- coding: utf-8 -*-
"""
예측 성공률 평가
--------------------------------------------------
(A) 예측 기록 → 실제 추첨 후 채점 → 전략별 누적 성공률
(B) 백테스트: 과거 데이터로 "그때 이 전략을 썼다면?"을 즉시 검증

로또 등수 규칙 (6/45):
  6개 일치            → 1등
  5개 + 보너스 일치   → 2등
  5개 일치            → 3등
  4개 일치            → 4등
  3개 일치            → 5등
  그 외               → 낙첨

사용법:
  python analysis/evaluate.py predict          # 다음 회차 예측을 전략별로 저장
  python analysis/evaluate.py predict 1231      # 특정 회차 대상으로 저장
  python analysis/evaluate.py score            # 추첨 완료된 예측 채점 + 누적 성공률
  python analysis/evaluate.py backtest 200      # 최근 200회로 전략별 성능 백테스트
"""

import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

# 같은 폴더의 recommend.py에서 전략 함수들을 그대로 가져다 쓴다.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from recommend import STRATEGIES  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "lotto.db"

RANK_NAMES = {1: "1등", 2: "2등", 3: "3등", 4: "4등", 5: "5등", 0: "낙첨"}


# ---------------------------------------------------------------------------
# 데이터 로드
# ---------------------------------------------------------------------------
def load_draws():
    """[(round, [n1..n6], bonus), ...] 오름차순."""
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT round, n1, n2, n3, n4, n5, n6, bonus FROM draws ORDER BY round"
    ).fetchall()
    conn.close()
    return [(r[0], list(r[1:7]), r[7]) for r in rows]


def draws_map(draws):
    return {rnd: (nums, bonus) for rnd, nums, bonus in draws}


def init_pred_table(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS predictions (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            target_round INTEGER,
            strategy     TEXT,
            n1 INTEGER, n2 INTEGER, n3 INTEGER,
            n4 INTEGER, n5 INTEGER, n6 INTEGER,
            matched      INTEGER,   -- 맞은 개수 (채점 전 NULL)
            rank         INTEGER,   -- 등수 0~6 (채점 전 NULL)
            UNIQUE(target_round, strategy)
        )
    """)
    conn.commit()


# ---------------------------------------------------------------------------
# 채점 로직
# ---------------------------------------------------------------------------
def grade(pred_nums, actual_nums, bonus):
    """예측 6개를 실제 당첨번호와 비교해 (맞은개수, 등수) 반환."""
    m = len(set(pred_nums) & set(actual_nums))
    if m == 6:
        rank = 1
    elif m == 5 and bonus in pred_nums:
        rank = 2
    elif m == 5:
        rank = 3
    elif m == 4:
        rank = 4
    elif m == 3:
        rank = 5
    else:
        rank = 0
    return m, rank


# ---------------------------------------------------------------------------
# (A) 예측 저장
# ---------------------------------------------------------------------------
def cmd_predict(target=None):
    draws = load_draws()
    latest = draws[-1][0]
    target = int(target) if target else latest + 1

    if target <= latest:
        print(f"주의: {target}회는 이미 추첨된 회차입니다. (참고용으로 저장)")

    # 예측에는 '대상 회차 이전까지'의 데이터만 사용
    history = [(r, n) for r, n, _ in draws if r < target]
    if not history:
        print("대상 회차 이전 데이터가 없습니다.")
        return

    conn = sqlite3.connect(DB_PATH)
    init_pred_table(conn)
    print(f"[{target}회 예측 저장] (예측 시점 데이터: 1~{history[-1][0]}회)\n")
    for name, (desc, fn) in STRATEGIES.items():
        nums = fn(history)
        conn.execute("""
            INSERT OR REPLACE INTO predictions
            (target_round, strategy, n1,n2,n3,n4,n5,n6, matched, rank)
            VALUES (?,?,?,?,?,?,?,?,NULL,NULL)
        """, (target, name, *nums))
        print(f"  [{name:9}] {'  '.join(f'{x:>2}' for x in nums)}")
    conn.commit()
    conn.close()
    print(f"\n저장 완료. 추첨 후 'python analysis/evaluate.py score' 로 채점하세요.")


# ---------------------------------------------------------------------------
# (A) 채점 + 누적 성공률
# ---------------------------------------------------------------------------
def cmd_score():
    draws = load_draws()
    dmap = draws_map(draws)

    conn = sqlite3.connect(DB_PATH)
    init_pred_table(conn)

    # 아직 채점 안 됐고, 실제 추첨이 끝난 예측을 채점
    rows = conn.execute(
        "SELECT id, target_round, strategy, n1,n2,n3,n4,n5,n6 FROM predictions WHERE rank IS NULL"
    ).fetchall()
    newly = 0
    for pid, tr, strat, *nums in rows:
        if tr not in dmap:
            continue  # 아직 추첨 전
        actual, bonus = dmap[tr]
        m, rank = grade(nums, actual, bonus)
        conn.execute("UPDATE predictions SET matched=?, rank=? WHERE id=?", (m, rank, pid))
        newly += 1
    conn.commit()

    if newly:
        print(f"새로 채점한 예측: {newly}건\n")

    # 전략별 누적 성적 집계
    graded = conn.execute(
        "SELECT strategy, matched, rank, target_round FROM predictions WHERE rank IS NOT NULL"
    ).fetchall()
    conn.close()

    if not graded:
        print("아직 채점된 예측이 없습니다. (예측 후 해당 회차가 추첨되면 채점됩니다)")
        return

    stats = defaultdict(lambda: {"n": 0, "match_sum": 0, "ranks": defaultdict(int)})
    for strat, m, rank, _ in graded:
        s = stats[strat]
        s["n"] += 1
        s["match_sum"] += m
        s["ranks"][rank] += 1

    print("=" * 60)
    print("  전략별 누적 예측 성적")
    print("=" * 60)
    print(f"  {'전략':10} {'예측수':>5} {'평균맞춤':>7} {'당첨(3+개)':>9}  등수분포")
    for strat, s in sorted(stats.items(), key=lambda x: -x[1]["match_sum"]/max(x[1]["n"],1)):
        n = s["n"]
        avg = s["match_sum"] / n
        wins = sum(c for r, c in s["ranks"].items() if r > 0)
        winrate = wins / n * 100
        rankstr = ", ".join(f"{RANK_NAMES[r]}×{s['ranks'][r]}"
                            for r in (1, 2, 3, 4, 5) if s["ranks"][r])
        print(f"  {strat:10} {n:>5} {avg:>7.2f} {winrate:>7.1f}%   {rankstr or '-'}")
    print("\n※ 참고용 지표입니다. 로또는 무작위라 장기적으론 어떤 전략도 무작위와 같습니다.")


# ---------------------------------------------------------------------------
# (B) 백테스트: 과거로 즉시 성능 검증
# ---------------------------------------------------------------------------
def cmd_backtest(n=200, sets_per=3):
    draws = load_draws()
    n = min(int(n), len(draws) - 10)
    targets = draws[-n:]  # 최근 n회차를 대상으로

    print("=" * 64)
    print(f"  백테스트: 최근 {n}회차 × 전략별 {sets_per}세트")
    print(f"  (각 회차마다 '그 이전 데이터만'으로 예측해 실제와 비교)")
    print("=" * 64)

    result = {name: {"match_sum": 0, "count": 0, "ranks": defaultdict(int)}
              for name in STRATEGIES}

    all_rounds = draws  # 이전 데이터 슬라이스용
    idx_by_round = {r: i for i, (r, _, _) in enumerate(all_rounds)}

    for tr, actual, bonus in targets:
        history = [(r, nm) for r, nm, _ in all_rounds[:idx_by_round[tr]]]
        if not history:
            continue
        for name, (_, fn) in STRATEGIES.items():
            for _ in range(sets_per):
                nums = fn(history)
                m, rank = grade(nums, actual, bonus)
                res = result[name]
                res["match_sum"] += m
                res["count"] += 1
                res["ranks"][rank] += 1

    print(f"  {'전략':10} {'평균맞춤':>7} {'5등이상률':>9} {'4등이상률':>9}  등수분포")
    for name in sorted(STRATEGIES, key=lambda x: -result[x]["match_sum"]/max(result[x]["count"],1)):
        res = result[name]
        c = res["count"]
        avg = res["match_sum"] / c
        win5 = sum(cnt for r, cnt in res["ranks"].items() if r in (1,2,3,4,5)) / c * 100
        win4 = sum(cnt for r, cnt in res["ranks"].items() if r in (1,2,3,4)) / c * 100
        rankstr = ", ".join(f"{RANK_NAMES[r]}×{res['ranks'][r]}"
                            for r in (1,2,3,4,5) if res["ranks"][r])
        print(f"  {name:10} {avg:>7.3f} {win5:>8.2f}% {win4:>8.2f}%   {rankstr or '-'}")
    print("\n해석: '평균맞춤'은 6개 중 평균 몇 개를 맞췄는지. 무작위 기대값은 약 0.80개입니다.")
    print("      전략 간 차이가 크지 않다면, 그게 정상입니다(로또는 무작위).")


def main():
    args = sys.argv[1:]
    cmd = args[0] if args else "score"
    if cmd == "predict":
        cmd_predict(args[1] if len(args) > 1 else None)
    elif cmd == "score":
        cmd_score()
    elif cmd == "backtest":
        cmd_backtest(args[1] if len(args) > 1 else 200)
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
