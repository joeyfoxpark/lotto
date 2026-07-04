# -*- coding: utf-8 -*-
"""
로또 6/45 패턴 통계 분석
--------------------------------------------------
data/lotto.db 를 읽어 다양한 패턴 통계를 계산하고,
 - 화면에 요약 리포트를 출력
 - data/stats.json 으로 저장 (나중에 앱에서 그대로 사용)

계산하는 패턴:
  1) 번호별 출현 빈도 (전체/최근)
  2) 미출현 기간 (각 번호가 마지막으로 나온 뒤 몇 회 지났나)
  3) 홀짝 비율 분포
  4) 번호 구간(1-10,11-20,...) 분포
  5) 연속 번호(연번) 등장 빈도
  6) 번호 합계 분포
  7) 궁합수 (자주 함께 나온 번호쌍 Top)

실행: python analysis/analyze.py
"""

import json
import sqlite3
from collections import Counter
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "lotto.db"
STATS_PATH = ROOT / "data" / "stats.json"

NUMS = range(1, 46)  # 로또 번호 1~45


def load_draws() -> list:
    """[(round, [n1..n6], bonus), ...] 를 회차 오름차순으로 반환."""
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT round, n1, n2, n3, n4, n5, n6, bonus FROM draws ORDER BY round"
    ).fetchall()
    conn.close()
    return [(r[0], list(r[1:7]), r[7]) for r in rows]


def frequency(draws, recent=None):
    """번호별 출현 빈도. recent=N이면 최근 N회차만 집계."""
    data = draws[-recent:] if recent else draws
    cnt = Counter()
    for _, nums, _ in data:
        cnt.update(nums)
    return {n: cnt.get(n, 0) for n in NUMS}


def not_appeared_gap(draws):
    """각 번호가 마지막으로 나온 뒤 지난 회차 수 (클수록 오래 안 나옴)."""
    last_round = {n: None for n in NUMS}
    for rnd, nums, _ in draws:
        for n in nums:
            last_round[n] = rnd
    newest = draws[-1][0]
    return {n: (newest - last_round[n] if last_round[n] else newest) for n in NUMS}


def odd_even_distribution(draws):
    """홀짝 개수 분포. 키 '홀:짝' -> 횟수."""
    dist = Counter()
    for _, nums, _ in draws:
        odd = sum(1 for n in nums if n % 2 == 1)
        dist[f"{odd}:{6 - odd}"] += 1
    return dict(sorted(dist.items(), key=lambda x: -x[1]))


def band_distribution(draws):
    """구간(1-10,11-20,21-30,31-40,41-45)별 번호 출현 총합."""
    bands = {"1-10": 0, "11-20": 0, "21-30": 0, "31-40": 0, "41-45": 0}
    for _, nums, _ in draws:
        for n in nums:
            if n <= 10: bands["1-10"] += 1
            elif n <= 20: bands["11-20"] += 1
            elif n <= 30: bands["21-30"] += 1
            elif n <= 40: bands["31-40"] += 1
            else: bands["41-45"] += 1
    return bands


def consecutive_count(draws):
    """연속 번호(예: 12,13)가 포함된 회차 수와 비율."""
    has_consec = 0
    for _, nums, _ in draws:
        s = sorted(nums)
        if any(s[i] + 1 == s[i + 1] for i in range(5)):
            has_consec += 1
    total = len(draws)
    return {"연번_포함_회차": has_consec, "전체": total,
            "비율(%)": round(has_consec / total * 100, 1)}


def sum_distribution(draws):
    """6개 번호 합계의 최소/최대/평균과 가장 흔한 합계 구간."""
    sums = [sum(nums) for _, nums, _ in draws]
    band = Counter((s // 20) * 20 for s in sums)  # 20단위 구간
    common = sorted(band.items(), key=lambda x: -x[1])[:3]
    return {
        "최소": min(sums), "최대": max(sums),
        "평균": round(sum(sums) / len(sums), 1),
        "많이_나온_합계구간": [f"{b}~{b+19} ({c}회)" for b, c in common],
    }


def companion_pairs(draws, top=10):
    """가장 자주 함께 나온 번호쌍 Top N (궁합수)."""
    pair = Counter()
    for _, nums, _ in draws:
        for a, b in combinations(sorted(nums), 2):
            pair[(a, b)] += 1
    return [{"pair": [a, b], "count": c}
            for (a, b), c in pair.most_common(top)]


def build_stats():
    draws = load_draws()
    total = len(draws)
    freq_all = frequency(draws)
    freq_recent = frequency(draws, recent=50)
    gap = not_appeared_gap(draws)

    stats = {
        "총회차": total,
        "최신회차": draws[-1][0],
        "빈도_전체": freq_all,
        "빈도_최근50": freq_recent,
        "미출현기간": gap,
        "홀짝분포": odd_even_distribution(draws),
        "구간분포": band_distribution(draws),
        "연속번호": consecutive_count(draws),
        "합계": sum_distribution(draws),
        "궁합수_top10": companion_pairs(draws, 10),
    }
    return stats, draws


def top_bottom(d, n=6):
    """딕셔너리(번호->값)에서 상위/하위 n개를 (번호,값) 리스트로."""
    items = sorted(d.items(), key=lambda x: -x[1])
    return items[:n], items[-n:]


def print_report(stats):
    print("=" * 55)
    print(f"  로또 6/45 통계 리포트  (1 ~ {stats['최신회차']}회, 총 {stats['총회차']}회)")
    print("=" * 55)

    hot, cold = top_bottom(stats["빈도_전체"])
    print("\n[전체 최다 출현 번호]")
    print("  " + ", ".join(f"{n}번({c}회)" for n, c in hot))
    print("[전체 최소 출현 번호]")
    print("  " + ", ".join(f"{n}번({c}회)" for n, c in cold))

    hotr, _ = top_bottom(stats["빈도_최근50"])
    print("\n[최근 50회 핫넘버]")
    print("  " + ", ".join(f"{n}번({c}회)" for n, c in hotr))

    longgap = sorted(stats["미출현기간"].items(), key=lambda x: -x[1])[:6]
    print("\n[오래 안 나온 번호 (미출현 회차)]")
    print("  " + ", ".join(f"{n}번({g}회 전)" for n, g in longgap))

    print("\n[홀짝 분포 Top3]")
    for k, v in list(stats["홀짝분포"].items())[:3]:
        print(f"  홀{k.split(':')[0]}:짝{k.split(':')[1]} -> {v}회")

    print("\n[번호 구간 분포]")
    for k, v in stats["구간분포"].items():
        print(f"  {k:>6} : {v}회")

    c = stats["연속번호"]
    print(f"\n[연속번호] 전체 {c['전체']}회 중 {c['연번_포함_회차']}회 포함 ({c['비율(%)']}%)")

    s = stats["합계"]
    print(f"\n[번호 합계] 최소 {s['최소']} / 평균 {s['평균']} / 최대 {s['최대']}")
    print("  많이 나온 합계구간: " + ", ".join(s["많이_나온_합계구간"]))

    print("\n[궁합수 Top10 (자주 함께 나온 쌍)]")
    for p in stats["궁합수_top10"]:
        print(f"  {p['pair'][0]:>2} & {p['pair'][1]:>2}  -> {p['count']}회")
    print()


def main():
    stats, _ = build_stats()
    print_report(stats)
    STATS_PATH.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"통계 저장 완료 -> {STATS_PATH}")


if __name__ == "__main__":
    main()
