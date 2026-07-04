# -*- coding: utf-8 -*-
"""
음력 -> 양력 변환 (사주 입력용)
--------------------------------------------------
사주는 반드시 '양력(솔라)' 날짜로 계산해야 하므로, 사용자가 음력 생일을
입력하면 먼저 양력으로 바꾼다. korean_lunar_calendar 라이브러리를 사용한다.
(한국천문연구원 데이터 기반, 1391~2050년 지원)
"""

from korean_lunar_calendar import KoreanLunarCalendar


def lunar_to_solar(y, m, d, is_leap=False):
    """음력(y,m,d, 윤달여부) -> 양력 (year, month, day) 튜플."""
    cal = KoreanLunarCalendar()
    ok = cal.setLunarDate(y, m, d, is_leap)
    if not ok:
        raise ValueError(f"변환 불가한 음력 날짜: {y}-{m}-{d} (윤달={is_leap})")
    iso = cal.SolarIsoFormat()  # 'YYYY-MM-DD'
    yy, mm, dd = map(int, iso.split("-"))
    return yy, mm, dd


def solar_to_lunar(y, m, d):
    """양력(y,m,d) -> 음력 (year, month, day, is_leap) — 참고 표시용."""
    cal = KoreanLunarCalendar()
    cal.setSolarDate(y, m, d)
    iso = cal.LunarIsoFormat()  # 'YYYY-MM-DD Intercalation' 형태
    parts = iso.replace("Intercalation", "L").split()
    yy, mm, dd = map(int, parts[0].split("-"))
    is_leap = len(parts) > 1 and parts[1] == "L"
    return yy, mm, dd, is_leap


def normalize_birth(y, m, d, calendar="solar", is_leap=False):
    """입력 달력 종류에 따라 항상 양력 (year, month, day)로 반환."""
    if calendar == "lunar":
        return lunar_to_solar(y, m, d, is_leap)
    return (y, m, d)


if __name__ == "__main__":
    # 검증: 음력 1990-04-21 -> 양력 1990-05-15
    print("음력 1990-04-21 ->", lunar_to_solar(1990, 4, 21), "(양력 1990-5-15 여야 함)")
    print("양력 1990-05-15 ->", solar_to_lunar(1990, 5, 15), "(음력 1990-4-21 여야 함)")
