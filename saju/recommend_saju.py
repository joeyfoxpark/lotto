# -*- coding: utf-8 -*-
"""
명리학(사주) 기반 로또 번호 추천
--------------------------------------------------
생년월일시로 사주팔자를 계산하고, 아래 명리 원리로 1~45 번호를 추천한다.

  1) 오행 수리(五行 數理): 번호의 끝자리를 오행에 배정
        1·6→수(水)  2·7→화(火)  3·8→목(木)  4·9→금(金)  5·0→토(土)
  2) 부족 오행 보완(용신 근사): 사주에 부족한 오행의 번호에 가중치를 준다.
  3) 그날의 일진(日辰): 추첨일의 일주 오행 기운을 추가로 반영한다.
  4) 결정성: 같은 사람 + 같은 추첨일이면 항상 같은 번호가 나온다.
        (사주는 무작위가 아니라 '정해진 기운'이므로)

  * 주의 *  이는 명리학을 응용한 '재미/참고용' 추천입니다. 로또는 무작위 추첨이라
  실제 당첨 확률과는 무관합니다.

사용법:
  python saju/recommend_saju.py 1990-05-15 07:30
  python saju/recommend_saju.py 1990-05-15 07:30 2026-07-11   # 추첨일 지정
  python saju/recommend_saju.py 1990-05-15                    # 태어난 시간 모름
"""

import hashlib
import sqlite3
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "lotto.db"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from saju_core import compute_saju, day_pillar, format_saju, GAN, GAN_OHENG, JI_OHENG  # noqa
import interpret  # noqa

# 번호 끝자리 -> 오행 (오행 수리)
DIGIT_OHENG = {1: "수", 6: "수", 2: "화", 7: "화", 3: "목", 8: "목",
               4: "금", 9: "금", 5: "토", 0: "토"}

OHENG_LIST = ["목", "화", "토", "금", "수"]


def number_oheng(n):
    return DIGIT_OHENG[n % 10]


def next_saturday(today=None):
    """추첨일(토요일) 기본값: 오늘 포함 이후 가장 가까운 토요일."""
    today = today or date.today()
    ahead = (5 - today.weekday()) % 7  # 월=0..일=6, 토=5
    return today + timedelta(days=ahead)


def _seed_int(text):
    """문자열 -> 결정적 정수 시드 (파이썬 기본 hash는 실행마다 달라 hashlib 사용)."""
    return int(hashlib.md5(text.encode("utf-8")).hexdigest(), 16)


class SeededRandom:
    """외부 의존 없는 결정적 난수 (선형 합동법). 같은 시드=같은 결과."""
    def __init__(self, seed):
        self.state = seed % (2**63)

    def _next(self):
        self.state = (self.state * 6364136223846793005 + 1442695040888963407) % (2**64)
        return self.state

    def weighted_pick_unique(self, weights: dict, k: int):
        chosen = []
        pool = dict(weights)
        for _ in range(k):
            total = sum(pool.values())
            r = self._next() % total
            acc = 0
            for num, w in pool.items():
                acc += w
                if r < acc:
                    chosen.append(num)
                    del pool[num]
                    break
        return sorted(chosen)


def recommend(birth_y, birth_m, birth_d, hour=None, draw_dt=None, count=6, opts=None):
    # 웹과 동일 기본값: 진태양시·서머타임 보정 ON, 출생지 서울
    if opts is None:
        opts = {"lon": 126.98, "precise": True, "nightZi": False}
    saju = compute_saju(birth_y, birth_m, birth_d, hour, opts=opts)
    draw_dt = draw_dt or next_saturday()

    # 추첨일의 일진(오행)
    dp, _ = day_pillar(draw_dt.year, draw_dt.month, draw_dt.day)
    draw_gan_oheng = GAN_OHENG[GAN.index(dp.gan)]
    draw_ji_oheng = JI_OHENG[dp.ji]

    # 오행별 가중치: 부족할수록 크게 (보완). 그날 일진 오행은 +부스트.
    oc = saju["oheng_count"]
    mx = max(oc.values())
    weight_oheng = {}
    for o in OHENG_LIST:
        base = (mx - oc[o]) + 1          # 부족 오행 보완
        boost = 0
        if o == draw_gan_oheng:
            boost += 2                     # 그날 천간 기운
        if o == draw_ji_oheng:
            boost += 1                     # 그날 지지 기운
        weight_oheng[o] = base + boost

    # 각 번호 가중치
    num_weights = {n: weight_oheng[number_oheng(n)] for n in range(1, 46)}

    # 결정적 시드: 사주 8글자 + 추첨일
    pillars_str = "".join(str(p) for p in saju["pillars"].values())
    seed = _seed_int(pillars_str + draw_dt.isoformat())
    rng = SeededRandom(seed)
    numbers = rng.weighted_pick_unique(num_weights, count)

    yongsin = max(weight_oheng.items(), key=lambda x: x[1])[0]
    return {
        "saju": saju,
        "draw_date": draw_dt,
        "draw_iljin": str(dp),
        "draw_oheng": (draw_gan_oheng, draw_ji_oheng),
        "weight_oheng": weight_oheng,
        "yongsin": yongsin,
        "numbers": numbers,
    }


def _region_data():
    """DB에서 지역별 1등 통계와 대표 명당을 읽는다 (없으면 None)."""
    try:
        conn = sqlite3.connect(DB_PATH)
        stats = {r[0]: r[1] for r in conn.execute(
            "SELECT region, COUNT(*) FROM winning_stores WHERE rank=1 AND region IS NOT NULL GROUP BY region")}
        rows = conn.execute("""
            SELECT region, name, COUNT(*) c FROM winning_stores
            WHERE rank=1 AND region IS NOT NULL AND name IS NOT NULL
            GROUP BY region, COALESCE(shop_id, name||address)""").fetchall()
        conn.close()
        top = {}
        for region, name, c in rows:
            top.setdefault(region, []).append((name, c))
        top = {rg: sorted(v, key=lambda x: -x[1])[:3] for rg, v in top.items()}
        return stats, top
    except Exception:
        return None, None


def print_result(res):
    print("=" * 56)
    print("  명리학(사주) 기반 로또 번호 추천")
    print("=" * 56)
    print(format_saju(res["saju"]))
    dg, dj = res["draw_oheng"]
    print(f"  추첨일     {res['draw_date']} (토)  일진 {res['draw_iljin']} "
          f"[{dg}·{dj} 기운]")
    print(f"  보완오행   " + "  ".join(f"{o}×{w}" for o, w in res['weight_oheng'].items())
          + "   (숫자 클수록 강조)")
    print("-" * 56)
    nums = res["numbers"]
    print("  추천번호   " + "   ".join(f"{n:>2}" for n in nums))
    print("             " + "   ".join(f"{number_oheng(n):>2}" for n in nums)
          + "   (각 번호의 오행)")
    st = res["saju"].get("solar_time")
    if st:
        print(f"  진태양시   {st}  (경도·균시차·서머타임 보정 반영)")
    print("=" * 56)

    # ---- 사주 풀이 ----
    stats, top = _region_data()
    sections = interpret.build_reading(
        res["saju"], res["draw_oheng"][0], res["yongsin"],
        res["draw_iljin"], stats, top)
    print("  [ 사주 풀이 ]")
    for title, lines in sections:
        print(f"  · {title}")
        for ln in lines:
            print(f"      {ln}")
    print("=" * 56)
    print("  ※ 계산(팔자·십신·십이운성)은 정통 규칙, 풀이·용신은 표준 원리 기반의")
    print("    간략 해석입니다. 로또는 무작위라 실제 당첨 확률과는 무관합니다.")


def parse_args(argv):
    if not argv:
        print("사용법: python saju/recommend_saju.py 생년월일[YYYY-MM-DD] [시간HH:MM] [추첨일YYYY-MM-DD]")
        print("예)     python saju/recommend_saju.py 1990-05-15 07:30")
        sys.exit(0)
    by, bm, bd = map(int, argv[0].split("-"))
    hour = None
    draw = None
    for a in argv[1:]:
        if ":" in a:
            hour = int(a.split(":")[0])
        elif "-" in a:
            yy, mm, dd = map(int, a.split("-"))
            draw = date(yy, mm, dd)
    return by, bm, bd, hour, draw


if __name__ == "__main__":
    by, bm, bd, hour, draw = parse_args(sys.argv[1:])
    res = recommend(by, bm, bd, hour, draw)
    print_result(res)
