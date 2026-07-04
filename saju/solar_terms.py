# -*- coding: utf-8 -*-
"""
절기(節氣) 정밀 계산 — 태양황경(Sun's apparent longitude) 기반
--------------------------------------------------
외부 라이브러리 없이 천문 공식(Meeus, 저정밀)으로 태양의 황경을 계산한다.
정밀도는 약 ±0.01°(≈15분)로, 사주의 월/년 경계 판정에 충분하다.

명리학에서 '월(月)'은 12절(節)로 나뉜다. 각 절은 태양황경이 특정 값을
지날 때 시작한다.
  입춘 315°(寅)  경칩 345°(卯)  청명 15°(辰)  입하 45°(巳)
  망종  75°(午)  소서 105°(未)  입추 135°(申)  백로 165°(酉)
  한로 195°(戌)  입동 225°(亥)  대설 255°(子)  소한 285°(丑)

시간대: 한국시(KST, UTC+9) 기준으로 입력받아 내부에서 UT로 변환해 계산한다.
"""

import math

# 12절의 (황경, 지지) — 입춘부터
JEOL = [
    (315, "인"), (345, "묘"), (15, "진"), (45, "사"),
    (75, "오"), (105, "미"), (135, "신"), (165, "유"),
    (195, "술"), (225, "해"), (255, "자"), (285, "축"),
]


def _jd_from_ut(y, m, d, hour=0, minute=0):
    """UT(세계시) 기준 율리우스일(JD)."""
    day = d + (hour + minute / 60.0) / 24.0
    if m <= 2:
        y -= 1
        m += 12
    a = y // 100
    b = 2 - a + a // 4
    return (math.floor(365.25 * (y + 4716)) + math.floor(30.6001 * (m + 1))
            + day + b - 1524.5)


def sun_longitude(jd):
    """해당 JD(UT)에서 태양의 겉보기 황경(0~360°)."""
    t = (jd - 2451545.0) / 36525.0
    # 평균 황경 / 평균 근점이각
    l0 = 280.46646 + 36000.76983 * t + 0.0003032 * t * t
    m = 357.52911 + 35999.05029 * t - 0.0001537 * t * t
    mr = math.radians(m % 360)
    # 중심차(equation of center)
    c = ((1.914602 - 0.004817 * t - 0.000014 * t * t) * math.sin(mr)
         + (0.019993 - 0.000101 * t) * math.sin(2 * mr)
         + 0.000289 * math.sin(3 * mr))
    true_long = l0 + c
    omega = 125.04 - 1934.136 * t
    apparent = true_long - 0.00569 - 0.00478 * math.sin(math.radians(omega))
    return apparent % 360.0


def _kst_to_jd(y, m, d, hour=12, minute=0):
    """한국시 -> JD(UT). KST = UT + 9h 이므로 UT = KST - 9h."""
    # 9시간을 빼서 UT로. 간단히 시/분에서 빼고 날짜 넘김은 JD 수식이 흡수.
    return _jd_from_ut(y, m, d, hour - 9, minute)


def solar_term_jd(year, target_deg, guess_month):
    """해당 연도에서 태양황경이 target_deg가 되는 시각의 JD(UT)를 이분법으로 찾음."""
    # 대략적인 시작 브래킷: 추정 월의 1일 ~ 다음달 초
    lo = _jd_from_ut(year, guess_month, 1) - 20
    hi = lo + 45  # 45일 창

    def f(jd):
        diff = (sun_longitude(jd) - target_deg + 180) % 360 - 180
        return diff

    flo, fhi = f(lo), f(hi)
    # 부호가 같으면 창을 넓혀본다
    if flo * fhi > 0:
        lo -= 20
        hi += 20
        flo, fhi = f(lo), f(hi)
    for _ in range(60):
        mid = (lo + hi) / 2
        fm = f(mid)
        if flo * fm <= 0:
            hi, fhi = mid, fm
        else:
            lo, flo = mid, fm
    return (lo + hi) / 2


def ipchun_jd(year):
    """해당 연도 입춘(황경 315°, 대략 2/4)의 JD(UT)."""
    return solar_term_jd(year, 315, 2)


def month_branch(y, m, d, hour=12, minute=0):
    """생년월일시(KST) -> 월지(月支). 태양황경으로 정확히 판정."""
    jd = _kst_to_jd(y, m, d, hour, minute)
    lam = sun_longitude(jd)
    # 315(입춘)부터 30°씩 끊어 12지지에 매핑
    idx = int(((lam - 315) % 360) // 30)
    return JEOL[idx][1]


def is_before_ipchun(y, m, d, hour=12, minute=0):
    """해당 시각이 그 해 입춘 이전인지 (년주 보정용)."""
    jd = _kst_to_jd(y, m, d, hour, minute)
    return jd < ipchun_jd(y)


def jd_to_kst_datetime(jd):
    """JD(UT) -> (년,월,일,시,분) KST 튜플 (검증/표시용)."""
    jd = jd + 9 / 24.0 + 0.5  # UT->KST, 그리고 0.5 보정
    z = math.floor(jd)
    f = jd - z
    if z < 2299161:
        a = z
    else:
        alpha = math.floor((z - 1867216.25) / 36524.25)
        a = z + 1 + alpha - math.floor(alpha / 4)
    b = a + 1524
    c = math.floor((b - 122.1) / 365.25)
    dd = math.floor(365.25 * c)
    e = math.floor((b - dd) / 30.6001)
    day = b - dd - math.floor(30.6001 * e)
    month = e - 1 if e < 14 else e - 13
    year = c - 4716 if month > 2 else c - 4715
    hour_f = f * 24
    hour = int(hour_f)
    minute = int(round((hour_f - hour) * 60))
    return year, month, day, hour, minute


if __name__ == "__main__":
    # 검증: 입춘/춘분/동지 시각 (알려진 값과 대조)
    print("[절기 정밀 계산 검증]")
    for yr in (2000, 2024, 2025):
        print(f"  {yr} 입춘 :", jd_to_kst_datetime(ipchun_jd(yr)), "KST")
    print("  2024 춘분(0°) :", jd_to_kst_datetime(solar_term_jd(2024, 0, 3)))
    print("  2020 동지(270°):", jd_to_kst_datetime(solar_term_jd(2020, 270, 12)))
    # 월지 검증
    print("  2000-01-01 월지:", month_branch(2000, 1, 1, 12), "(자 이어야 함)")
    print("  1990-05-15 월지:", month_branch(1990, 5, 15, 7), "(사 이어야 함)")
