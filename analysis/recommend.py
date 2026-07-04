# -*- coding: utf-8 -*-
"""
로또 6/45 번호 추천 엔진
--------------------------------------------------
data/lotto.db 통계를 바탕으로 여러 '패턴 전략'으로 번호를 추천한다.

  * 중요 *  로또는 매 회차 완전한 무작위 추첨이라, 어떤 전략도 실제 당첨
  확률을 높이지 못한다. 이 추천은 '재미/참고용' 이다. (앱에서도 반드시
  이 문구를 표시할 것 — 과대광고는 법적 문제가 될 수 있다.)

제공 전략:
  hot      : 자주 나온 번호에 가중치를 둬서 추천
  cold     : 오래 안 나온(미출현) 번호에 가중치
  balanced : 홀짝 3:3 · 구간 고르게 · 합계 정상범위를 만족하는 무작위
  companion: 궁합수(자주 함께 나온 쌍)에서 시작해 확장
  random   : 완전 무작위 (기준선)

실행:
  python analysis/recommend.py            # 전략별로 한 세트씩
  python analysis/recommend.py balanced 5 # balanced 전략으로 5세트
"""

import random
import sqlite3
import sys
from collections import Counter
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "lotto.db"
NUMS = list(range(1, 46))


def load_draws():
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT round, n1, n2, n3, n4, n5, n6 FROM draws ORDER BY round"
    ).fetchall()
    conn.close()
    return [(r[0], list(r[1:7])) for r in rows]


def band_of(n):
    return (n - 1) // 10 if n <= 40 else 4  # 0~4 (마지막은 41-45)


def is_realistic(nums):
    """실제 당첨 조합에서 흔한 조건을 만족하는지 (통계적 필터)."""
    s = sorted(nums)
    total = sum(s)
    if not (100 <= total <= 175):          # 합계 정상범위(가장 흔한 구간)
        return False
    odd = sum(1 for n in s if n % 2)
    if odd in (0, 6):                       # 전부 홀 또는 전부 짝 제외
        return False
    if len(set(band_of(n) for n in s)) < 3: # 최소 3개 구간에 분산
        return False
    if any(s[i] + 1 == s[i+1] and s[i+1] + 1 == s[i+2] for i in range(4)):
        return False                        # 3연속 번호 제외
    return True


def weighted_pick(weights, k=6):
    """번호별 가중치 dict에서 중복 없이 k개 뽑기."""
    pool, w = list(weights.keys()), list(weights.values())
    picked = set()
    while len(picked) < k:
        picked.add(random.choices(pool, weights=w, k=1)[0])
    return sorted(picked)


def strategy_hot(draws):
    cnt = Counter()
    for _, nums in draws:
        cnt.update(nums)
    weights = {n: cnt.get(n, 1) ** 2 for n in NUMS}  # 빈도 제곱으로 강조
    return weighted_pick(weights)


def strategy_cold(draws):
    last = {n: 0 for n in NUMS}
    for rnd, nums in draws:
        for n in nums:
            last[n] = rnd
    newest = draws[-1][0]
    gap = {n: (newest - last[n] + 1) for n in NUMS}
    weights = {n: gap[n] ** 2 for n in NUMS}         # 오래 안 나올수록 가중
    return weighted_pick(weights)


def strategy_balanced(draws):
    for _ in range(2000):
        cand = sorted(random.sample(NUMS, 6))
        if is_realistic(cand):
            return cand
    return sorted(random.sample(NUMS, 6))


def strategy_companion(draws):
    pair = Counter()
    for _, nums in draws:
        for a, b in combinations(sorted(nums), 2):
            pair[(a, b)] += 1
    top = [p for p, _ in pair.most_common(40)]
    a, b = random.choice(top)                        # 인기 궁합쌍에서 시작
    chosen = {a, b}
    cnt = Counter()
    for _, nums in draws:
        cnt.update(nums)
    weights = {n: cnt.get(n, 1) for n in NUMS if n not in chosen}
    while len(chosen) < 6:
        chosen.add(random.choices(list(weights), weights=list(weights.values()), k=1)[0])
    return sorted(chosen)


def strategy_random(draws):
    return sorted(random.sample(NUMS, 6))


PRIMES = {2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43}


def strategy_lowhigh(draws):
    """저(1~22) 3개 + 고(23~45) 3개."""
    low = random.sample(range(1, 23), 3)
    high = random.sample(range(23, 46), 3)
    return sorted(low + high)


def strategy_ending(draws):
    """끝자리가 서로 다르게(분산)."""
    for _ in range(800):
        c = random.sample(NUMS, 6)
        if len({n % 10 for n in c}) >= 5:
            return sorted(c)
    return sorted(random.sample(NUMS, 6))


def strategy_prime(draws):
    """소수(2,3,5,7…) 선호."""
    weights = {n: (6 if n in PRIMES else 1) for n in NUMS}
    return weighted_pick(weights)


def strategy_trend(draws):
    """최근 10회에 많이 나온 번호."""
    weights = {n: 1 for n in NUMS}
    for _, nums in draws[-10:]:
        for n in nums:
            weights[n] += 4
    return weighted_pick(weights)


def strategy_overdue(draws):
    """가장 오래 안 나온 15개 중에서."""
    last = {n: 0 for n in NUMS}
    for rnd, nums in draws:
        for n in nums:
            last[n] = rnd
    newest = draws[-1][0]
    top = [n for n, _ in sorted(((n, newest - last[n]) for n in NUMS),
                                key=lambda x: -x[1])[:15]]
    return sorted(random.sample(top, 6))


def strategy_sumband(draws):
    """합계가 흔한 구간(105~145)."""
    for _ in range(3000):
        c = random.sample(NUMS, 6)
        if 105 <= sum(c) <= 145:
            return sorted(c)
    return sorted(random.sample(NUMS, 6))


def strategy_fresh(draws):
    """직전 회차 번호 제외 + 현실적 조합."""
    prev = set(draws[-1][1])
    for _ in range(3000):
        c = random.sample(NUMS, 6)
        if prev & set(c):
            continue
        if is_realistic(c):
            return sorted(c)
    return sorted(random.sample(NUMS, 6))


def strategy_perfect(draws):
    """홀짝3:3 + 저고3:3 + 합100~170 + 4구간이상."""
    for _ in range(8000):
        c = sorted(random.sample(NUMS, 6))
        odd = sum(1 for n in c if n % 2)
        low = sum(1 for n in c if n <= 22)
        if (odd == 3 and low == 3 and 100 <= sum(c) <= 170
                and len({band_of(n) for n in c}) >= 4):
            return c
    return strategy_balanced(draws)


STRATEGIES = {
    "hot": ("핫넘버·자주 나온 번호", strategy_hot),
    "cold": ("콜드넘버·오래 안 나온 번호", strategy_cold),
    "trend": ("최근트렌드·최근 10회 강조", strategy_trend),
    "overdue": ("장기미출현 위주", strategy_overdue),
    "balanced": ("균형·홀짝/구간/합계", strategy_balanced),
    "perfect": ("완벽밸런스·홀짝3:3 저고3:3", strategy_perfect),
    "lowhigh": ("저고균형·낮은수3 높은수3", strategy_lowhigh),
    "sumband": ("합계중심·합105~145", strategy_sumband),
    "ending": ("끝수분산·끝자리 골고루", strategy_ending),
    "companion": ("궁합수 기반 확장", strategy_companion),
    "prime": ("소수 선호", strategy_prime),
    "fresh": ("이월제외·직전회차 제외", strategy_fresh),
    "random": ("완전 무작위(기준선)", strategy_random),
}


def main():
    draws = load_draws()
    args = sys.argv[1:]

    if args and args[0] in STRATEGIES:
        name = args[0]
        count = int(args[1]) if len(args) > 1 else 5
        desc, fn = STRATEGIES[name]
        print(f"[{name}] {desc} — {count}세트\n")
        for i in range(count):
            print(f"  {i+1}. " + "  ".join(f"{n:>2}" for n in fn(draws)))
    else:
        print("=== 전략별 추천 번호 (각 1세트) ===\n")
        for name, (desc, fn) in STRATEGIES.items():
            nums = fn(draws)
            print(f"  [{name:9}] {'  '.join(f'{n:>2}' for n in nums)}   ({desc})")

    print("\n※ 로또는 완전 무작위 추첨입니다. 재미로만 참고하세요.")


if __name__ == "__main__":
    main()
