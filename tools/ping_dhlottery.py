# -*- coding: utf-8 -*-
"""동행복권이 (깃허브 등) 현재 서버 IP에서 접근 가능한지 진단."""
import requests

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

# 실행 서버의 IP/위치
try:
    ip = requests.get("https://api.ipify.org", timeout=10).text
    geo = requests.get(f"http://ip-api.com/json/{ip}", timeout=10).json()
    print(f"[runner] IP={ip}  country={geo.get('country')}  isp={geo.get('isp')}")
except Exception as e:
    print("[runner] IP 조회 실패:", e)

s = requests.Session()
s.headers.update({"User-Agent": UA, "Accept-Language": "ko-KR,ko;q=0.9",
                  "X-Requested-With": "XMLHttpRequest",
                  "Referer": "https://www.dhlottery.co.kr/lt645/result"})

ok = False
try:
    s.get("https://www.dhlottery.co.kr/lt645/result",
          headers={"User-Agent": UA}, timeout=20)
    r = s.get("https://www.dhlottery.co.kr/lt645/selectPstLt645InfoNew.do",
              params={"srchDir": "center", "srchLtEpsd": "1200"}, timeout=20)
    print("draw API:", r.status_code, r.headers.get("Content-Type"))
    lst = (r.json().get("data") or {}).get("list") or []
    print("회차 수신:", len(lst))
    if lst:
        print("샘플:", lst[0].get("ltEpsd"), "회 ->",
              [lst[0].get(f"tm{i}WnNo") for i in range(1, 7)])
        ok = True
except Exception as e:
    print("draw API 실패:", type(e).__name__, e)

print("\n결과:", "✅ 접근 가능 (클라우드 자동수집 가능)" if ok
      else "❌ 차단/실패 (하이브리드 필요)")
raise SystemExit(0 if ok else 1)
