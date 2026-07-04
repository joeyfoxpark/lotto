# -*- coding: utf-8 -*-
"""
사주팔자(四柱八字) 계산 엔진
--------------------------------------------------
생년월일 + 태어난 시간을 입력받아 년주·월주·일주·시주(8글자)와
각 글자의 오행(五行)을 계산한다.

정확도 관련 참고:
 - 일주(日柱): 1900-01-01 = 갑술(甲戌)일 을 기준으로 60갑자를 이어서 계산.
   (검증: 이 기준으로 2000-01-01의 일간이 戊(무)로 나오며 만세력과 일치)
 - 년주/월주: 입춘(立春) 및 12절기(節氣)를 '근사 날짜'로 처리한다.
   실제 절기는 해마다 1~2일 다를 수 있어, 절기 경계일 태생은 만세력과
   하루 차이가 날 수 있다. (엔터테인먼트 목적에는 충분)
 - 시주(時柱): 자시(23:00~00:59) 야자시/조자시 구분은 단순화(날짜 안 넘김).
"""

import math
from dataclasses import dataclass
from datetime import date, timedelta

from solar_terms import month_branch as _precise_month_branch
from solar_terms import is_before_ipchun as _precise_before_ipchun

# 주요 도시 경도 (진태양시 경도보정용)
CITY_LON = {
    "서울": 126.98, "인천": 126.71, "수원": 127.03, "춘천": 127.73, "강릉": 128.90,
    "대전": 127.38, "세종": 127.29, "청주": 127.49, "전주": 127.15, "광주": 126.85,
    "목포": 126.39, "대구": 128.60, "부산": 129.08, "울산": 129.31, "창원": 128.68,
    "제주": 126.53, "개성/평양": 125.9,
}
# 대한민국 서머타임 시행 구간(양력 대략)
_DST_RANGES = [
    ((1948, 5, 31), (1948, 9, 13)), ((1949, 4, 3), (1949, 9, 11)),
    ((1950, 4, 1), (1950, 9, 10)), ((1951, 5, 6), (1951, 9, 9)),
    ((1955, 5, 5), (1955, 9, 9)), ((1956, 5, 20), (1956, 9, 30)),
    ((1957, 5, 5), (1957, 9, 22)), ((1958, 5, 4), (1958, 9, 21)),
    ((1959, 5, 3), (1959, 9, 20)), ((1960, 5, 1), (1960, 9, 18)),
    ((1987, 5, 10), (1987, 10, 11)), ((1988, 5, 8), (1988, 10, 9)),
]


def equation_of_time(y, m, d):
    """균시차(분): 겉보기 태양시 - 평균 태양시."""
    n = date(y, m, d).timetuple().tm_yday
    b = 2 * math.pi * (n - 81) / 365
    return 9.87 * math.sin(2 * b) - 7.53 * math.cos(b) - 1.5 * math.sin(b)


def is_korean_dst(y, m, d):
    t = date(y, m, d)
    return any(date(*a) <= t < date(*b) for a, b in _DST_RANGES)


def _add_minutes(y, m, d, total):
    """(y,m,d) 자정 기준 total분 뒤의 (년,월,일,시,분). 음수/날짜 넘김 처리."""
    off = math.floor(total / 1440)
    mm = total - off * 1440
    nd = date(y, m, d) + timedelta(days=off)
    return nd.year, nd.month, nd.day, int(mm // 60), int(round(mm % 60))

# 천간(天干) 10 / 지지(地支) 12
GAN = ["갑", "을", "병", "정", "무", "기", "경", "신", "임", "계"]
JI = ["자", "축", "인", "묘", "진", "사", "오", "미", "신", "유", "술", "해"]

# 오행(五行)
GAN_OHENG = ["목", "목", "화", "화", "토", "토", "금", "금", "수", "수"]  # 갑을=목 ...
JI_OHENG = {
    "인": "목", "묘": "목", "사": "화", "오": "화",
    "진": "토", "술": "토", "축": "토", "미": "토",
    "신": "금", "유": "금", "자": "수", "해": "수",
}

# 일주 기준: 1900-01-01 = 갑술(甲戌). 60갑자 index(0=갑자)에서 갑술 = 10.
_ANCHOR = date(1900, 1, 1)
_ANCHOR_INDEX = 10  # 갑술

@dataclass
class Pillar:
    gan: str      # 천간
    ji: str       # 지지
    def __str__(self):
        return f"{self.gan}{self.ji}"
    def oheng(self):
        gi = GAN.index(self.gan)
        return GAN_OHENG[gi], JI_OHENG[self.ji]


def year_pillar(y, m, d, hour=12, minute=0):
    """년주. 정밀 입춘 시각 기준으로 연도 보정."""
    before_ipchun = _precise_before_ipchun(y, m, d, hour, minute)
    yy = y - 1 if before_ipchun else y
    gi = (yy - 4) % 10
    ji = (yy - 4) % 12
    return Pillar(GAN[gi], JI[ji]), yy


def month_pillar(y, m, d, hour=12, minute=0):
    """월주. 월지는 정밀 절기로, 월간은 오호둔(년간)으로."""
    branch = _precise_month_branch(y, m, d, hour, minute)
    _, mingli_year = year_pillar(y, m, d, hour, minute)
    year_gan_idx = (mingli_year - 4) % 10
    # 寅월(인월) 천간 = (년간%5)*2 + 2  (甲己→丙 ...)
    in_wol_gan = ((year_gan_idx % 5) * 2 + 2) % 10
    # 인월부터의 순서 (인=0, 묘=1, ... 자=10, 축=11)
    order = ["인", "묘", "진", "사", "오", "미", "신", "유", "술", "해", "자", "축"]
    step = order.index(branch)
    gan_idx = (in_wol_gan + step) % 10
    return Pillar(GAN[gan_idx], branch)


def day_pillar(y, m, d):
    """일주. 1900-01-01=갑술 기준 연속 60갑자."""
    delta = (date(y, m, d) - _ANCHOR).days
    idx = (_ANCHOR_INDEX + delta) % 60
    return Pillar(GAN[idx % 10], JI[idx % 12]), idx


def hour_pillar(day_gan, hour, minute=0):
    """시주. 시지는 2시간 단위, 시간은 오자둔(일간)으로. hour=None이면 미상."""
    if hour is None:
        return None
    # 시지: 子시 23:00~00:59, 丑 01~02:59, ...
    h = hour
    ji_order = ["자", "축", "인", "묘", "진", "사", "오", "미", "신", "유", "술", "해"]
    # (h+1)//2 % 12 => 23,0->자 / 1,2->축 ...
    ji_idx = ((h + 1) // 2) % 12
    branch = ji_order[ji_idx]
    day_gan_idx = GAN.index(day_gan)
    # 子시 천간 = (일간%5)*2  (甲己→甲子 ...)
    ja_si_gan = ((day_gan_idx % 5) * 2) % 10
    gan_idx = (ja_si_gan + ji_idx) % 10
    return Pillar(GAN[gan_idx], branch)


def compute_saju(y, m, d, hour=None, minute=0, opts=None):
    """생년월일시 -> 4주(년/월/일/시)와 오행 분포를 담은 dict.

    opts: {"lon": 경도, "precise": 진태양시·서머타임 보정, "nightZi": 야자시}
    """
    opts = {"lon": 135, "precise": False, "nightZi": False, **(opts or {})}
    known = hour is not None
    clock_min = (hour if known else 12) * 60 + (minute or 0)
    dst_adj = -60 if (opts["precise"] and is_korean_dst(y, m, d)) else 0

    # (1) 물리적 시각(절기=년·월주용): 서머타임만 보정
    phys = _add_minutes(y, m, d, clock_min + dst_adj)
    # (2) 지방진태양시(시주·일주경계용): +경도보정 +균시차
    sol_adj = ((opts["lon"] - 135) * 4 + equation_of_time(y, m, d)) if opts["precise"] else 0
    sol = _add_minutes(y, m, d, clock_min + dst_adj + sol_adj)

    day_ymd = (sol[0], sol[1], sol[2])
    if known and opts["nightZi"] and sol[3] >= 23:      # 야자시: 다음날 일주
        s = _add_minutes(sol[0], sol[1], sol[2], 24 * 60)
        day_ymd = (s[0], s[1], s[2])

    yp, _ = year_pillar(phys[0], phys[1], phys[2], phys[3], phys[4])
    mp = month_pillar(phys[0], phys[1], phys[2], phys[3], phys[4])
    dp, _ = day_pillar(*day_ymd)
    hp = hour_pillar(dp.gan, sol[3], sol[4]) if known else None

    pillars = {"년주": yp, "월주": mp, "일주": dp}
    if hp:
        pillars["시주"] = hp

    oheng_count = {"목": 0, "화": 0, "토": 0, "금": 0, "수": 0}
    for p in pillars.values():
        go, jo = p.oheng()
        oheng_count[go] += 1
        oheng_count[jo] += 1

    return {
        "pillars": pillars,
        "ilgan": dp.gan,            # 일간(자기 자신) — 사주 해석의 중심
        "oheng_count": oheng_count,
        "solar_time": (f"{sol[3]:02d}:{sol[4]:02d}" if known else None),
    }


def format_saju(result):
    """사람이 읽기 좋은 문자열로."""
    ps = result["pillars"]
    order = ["시주", "일주", "월주", "년주"]
    line = "   ".join(f"{k}:{ps[k]}" for k in order if k in ps)
    oh = result["oheng_count"]
    ohline = "  ".join(f"{k}{v}" for k, v in oh.items())
    lack = [k for k, v in oh.items() if v == 0]
    lackline = ("부족한 오행: " + ", ".join(lack)) if lack else "오행이 고루 분포"
    return (f"  사주팔자   {line}\n"
            f"  일간(나)   {result['ilgan']}\n"
            f"  오행분포   {ohline}   ({lackline})")


if __name__ == "__main__":
    # 검증용 샘플: 2000-01-01 12:00 -> 일주는 무오(戊午) 여야 함
    r = compute_saju(2000, 1, 1, 12)
    print("[검증] 2000-01-01 12:00")
    print(format_saju(r))
    print("  -> 일주가 '무오'면 일주 계산 정확 (만세력과 일치)")
