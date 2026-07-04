# -*- coding: utf-8 -*-
"""
우리 사주 엔진 vs lunar-python(정통 규칙 라이브러리) 교차검증
--------------------------------------------------
표준시 기준(진태양시 보정 OFF)으로 두 엔진의 팔자가 일치하는지 대량 비교한다.
진태양시는 한국식 추가 보정이므로 순수 팔자 계산 정확도만 대조한다.

실행: python saju/verify_engine.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from saju_core import compute_saju
from lunar_python import Solar

# 한자 -> 한글 매핑
CN_GAN = dict(zip("甲乙丙丁戊己庚辛壬癸", "갑을병정무기경신임계"))
CN_JI = dict(zip("子丑寅卯辰巳午未申酉戌亥", "자축인묘진사오미신유술해"))


def cn_to_kr(pillar_cn):
    """己卯 -> 기묘"""
    return CN_GAN[pillar_cn[0]] + CN_JI[pillar_cn[1]]


def theirs(y, m, d, h):
    ec = Solar.fromYmdHms(y, m, d, h, 0, 0).getLunar().getEightChar()
    return (cn_to_kr(ec.getYear()), cn_to_kr(ec.getMonth()),
            cn_to_kr(ec.getDay()), cn_to_kr(ec.getTime()))


def ours(y, m, d, h):
    r = compute_saju(y, m, d, h, opts={"precise": False, "lon": 135})
    p = r["pillars"]
    return (str(p["년주"]), str(p["월주"]), str(p["일주"]), str(p["시주"]))


def main():
    # 광범위 샘플: 연도×월×일×시 격자 (절기 경계 포함)
    total = 0
    mismatch = []
    years = list(range(1930, 2026, 7))
    months = [1, 2, 3, 5, 8, 11, 12]
    days = [3, 5, 8, 15, 22]      # 절기 경계 근처 포함
    hours = [1, 7, 12, 18, 22]
    labels = ["년주", "월주", "일주", "시주"]

    for y in years:
        for m in months:
            for d in days:
                for h in hours:
                    total += 1
                    o, t = ours(y, m, d, h), theirs(y, m, d, h)
                    if o != t:
                        diff = [labels[i] for i in range(4) if o[i] != t[i]]
                        mismatch.append((y, m, d, h, o, t, diff))

    print(f"총 {total}건 비교")
    print(f"일치 {total - len(mismatch)}건 / 불일치 {len(mismatch)}건 "
          f"({(total-len(mismatch))/total*100:.2f}%)")
    if mismatch:
        # 불일치 어느 기둥에서 나는지 집계
        from collections import Counter
        c = Counter()
        for *_, diff in mismatch:
            for pil in diff:
                c[pil] += 1
        print("불일치 기둥 분포:", dict(c))
        print("\n샘플 불일치 20건:")
        for y, m, d, h, o, t, diff in mismatch[:20]:
            print(f"  {y}-{m:02d}-{d:02d} {h:02d}시 | 우리 {o} | lunar {t} | 차이 {diff}")


if __name__ == "__main__":
    main()
