# -*- coding: utf-8 -*-
"""
로또 번호 추천 웹 서비스 (Flask)
--------------------------------------------------
지금까지 만든 로직(수집/통계/추천/사주/판매점)을 웹으로 제공한다.

실행:
  python web/app.py
브라우저에서  http://127.0.0.1:5000  접속

주요 페이지:
  /            홈 (최신 회차 요약)
  /stats       패턴 통계
  /recommend   패턴별 번호 추천
  /saju        사주(명리학) 기반 추천 — 음력/양력, 시간 선택
  /stores      당첨 판매점 (명당 랭킹 + 회차 조회)
  /predict     예측 성공률 (백테스트)
"""

import sqlite3
import sys
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

from flask import Flask, render_template, request, jsonify

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "lotto.db"

# 기존 로직 모듈들 경로 추가
sys.path.insert(0, str(ROOT / "analysis"))
sys.path.insert(0, str(ROOT / "saju"))
sys.path.insert(0, str(ROOT / "collector"))

import recommend as rec              # analysis/recommend.py
from analyze import build_stats      # analysis/analyze.py
from evaluate import grade           # analysis/evaluate.py
import recommend_saju as rsaju       # saju/recommend_saju.py
from saju_core import compute_saju, format_saju
from lunar import normalize_birth, solar_to_lunar
import collect_stores as cstore      # collector/collect_stores.py

app = Flask(__name__)

# 간단한 메모리 캐시 (통계/백테스트는 매번 계산하면 느리므로)
_cache = {}


# ---------------------------------------------------------------------------
# 공통 헬퍼
# ---------------------------------------------------------------------------
def db():
    conn = sqlite3.connect(DB_PATH, timeout=60)
    conn.execute("PRAGMA busy_timeout=60000")
    conn.row_factory = sqlite3.Row
    return conn


def latest_draw():
    conn = db()
    row = conn.execute("SELECT * FROM draws ORDER BY round DESC LIMIT 1").fetchone()
    conn.close()
    return row


def get_stats():
    if "stats" not in _cache:
        _cache["stats"], _ = build_stats()
    return _cache["stats"]


def next_saturday(today=None):
    today = today or date.today()
    return today + timedelta(days=(5 - today.weekday()) % 7)


# ---------------------------------------------------------------------------
# 페이지: 홈
# ---------------------------------------------------------------------------
@app.route("/")
def home():
    row = latest_draw()
    nums = [row[f"n{i}"] for i in range(1, 7)] if row else []
    return render_template("index.html",
                           latest=row, numbers=nums,
                           total=row["round"] if row else 0)


# ---------------------------------------------------------------------------
# 페이지: 통계
# ---------------------------------------------------------------------------
@app.route("/stats")
def stats_page():
    s = get_stats()
    freq = s["빈도_전체"]
    freq_sorted = sorted(freq.items(), key=lambda x: -x[1])
    recent = sorted(s["빈도_최근50"].items(), key=lambda x: -x[1])[:8]
    gap = sorted(s["미출현기간"].items(), key=lambda x: -x[1])[:8]
    return render_template("stats.html", stats=s,
                           freq=freq, freq_max=max(freq.values()),
                           hot=freq_sorted[:8], cold=freq_sorted[-8:],
                           recent=recent, gap=gap)


# ---------------------------------------------------------------------------
# 페이지: 패턴 추천
# ---------------------------------------------------------------------------
@app.route("/recommend")
def recommend_page():
    draws = rec.load_draws()
    sets = {}
    for name, (desc, fn) in rec.STRATEGIES.items():
        sets[name] = {"desc": desc, "nums": fn(draws)}
    return render_template("recommend.html", sets=sets)


@app.route("/api/recommend")
def api_recommend():
    """AJAX용: ?strategy=balanced&count=5 -> JSON 세트 목록."""
    draws = rec.load_draws()
    name = request.args.get("strategy", "balanced")
    count = min(int(request.args.get("count", 5)), 20)
    if name not in rec.STRATEGIES:
        return jsonify({"error": "unknown strategy"}), 400
    fn = rec.STRATEGIES[name][1]
    return jsonify({"strategy": name, "sets": [fn(draws) for _ in range(count)]})


# ---------------------------------------------------------------------------
# 페이지: 사주 추천
# ---------------------------------------------------------------------------
@app.route("/saju", methods=["GET", "POST"])
def saju_page():
    ctx = {"result": None, "form": {}}
    if request.method == "POST":
        f = request.form
        ctx["form"] = f
        try:
            y, m, d = int(f["year"]), int(f["month"]), int(f["day"])
            calendar = f.get("calendar", "solar")
            is_leap = f.get("is_leap") == "on"
            # 음력이면 양력으로 변환
            sy, sm, sd = normalize_birth(y, m, d, calendar, is_leap)
            hour = None if f.get("hour", "") in ("", "unknown") else int(f["hour"])
            draw = None
            if f.get("draw_date"):
                yy, mm, dd = map(int, f["draw_date"].split("-"))
                draw = date(yy, mm, dd)
            res = rsaju.recommend(sy, sm, sd, hour, draw)
            # 화면 표시용 가공
            ctx["result"] = {
                "solar": f"{sy}-{sm:02d}-{sd:02d}",
                "calendar": calendar,
                "saju_text": format_saju(res["saju"]),
                "pillars": {k: str(v) for k, v in res["saju"]["pillars"].items()},
                "oheng": res["saju"]["oheng_count"],
                "ilgan": res["saju"]["ilgan"],
                "draw_date": res["draw_date"].isoformat(),
                "draw_iljin": res["draw_iljin"],
                "numbers": res["numbers"],
                "num_oheng": [rsaju.number_oheng(n) for n in res["numbers"]],
            }
        except Exception as e:
            ctx["error"] = f"입력을 확인해 주세요: {e}"
    ctx["default_draw"] = next_saturday().isoformat()
    return render_template("saju.html", **ctx)


# ---------------------------------------------------------------------------
# 페이지: 당첨 판매점
# ---------------------------------------------------------------------------
@app.route("/stores")
def stores_page():
    conn = db()
    # 명당 랭킹: 1등 배출 횟수 Top
    ranking = conn.execute("""
        SELECT name, region,
               COUNT(*) AS wins,
               MAX(address) AS address
        FROM winning_stores
        WHERE rank=1 AND name IS NOT NULL
        GROUP BY COALESCE(shop_id, name || address)
        ORDER BY wins DESC, name
        LIMIT 50
    """).fetchall()
    have_rounds = conn.execute("SELECT COUNT(DISTINCT round) FROM winning_stores WHERE rank=1").fetchone()[0]
    conn.close()
    return render_template("stores.html", ranking=ranking, have_rounds=have_rounds)


@app.route("/stores/round")
def stores_round():
    """특정 회차 1·2등 판매점 (DB에 없으면 실시간 조회)."""
    rnd = int(request.args.get("round", latest_draw()["round"]))
    conn = db()
    result = {}
    for rank in (1, 2):
        rows = conn.execute(
            "SELECT name, region, address, tel, auto_type FROM winning_stores "
            "WHERE round=? AND rank=? ORDER BY seq", (rnd, rank)).fetchall()
        if not rows:  # DB에 없으면 실시간 수집 후 저장
            s = cstore.make_session()
            items = cstore.fetch_stores(s, rnd, rank)
            cstore.init_table(conn)
            cstore.save(conn, rnd, rank, items)
            rows = conn.execute(
                "SELECT name, region, address, tel, auto_type FROM winning_stores "
                "WHERE round=? AND rank=? ORDER BY seq", (rnd, rank)).fetchall()
        result[rank] = [dict(r) for r in rows]
    conn.close()
    return jsonify({"round": rnd, "rank1": result[1], "rank2": result[2]})


# ---------------------------------------------------------------------------
# 페이지: 예측 성공률 (백테스트)
# ---------------------------------------------------------------------------
def run_backtest(n=100, sets_per=1):
    key = f"bt_{n}_{sets_per}"
    if key in _cache:
        return _cache[key]
    conn = db()
    rows = conn.execute(
        "SELECT round, n1,n2,n3,n4,n5,n6, bonus FROM draws ORDER BY round").fetchall()
    conn.close()
    draws_full = [(r["round"], [r[f"n{i}"] for i in range(1, 7)], r["bonus"]) for r in rows]
    targets = draws_full[-n:]
    idx = {r[0]: i for i, r in enumerate(draws_full)}

    result = {name: {"match": 0, "cnt": 0, "win5": 0}
              for name in rec.STRATEGIES}
    for tr, actual, bonus in targets:
        history = [(r, nm) for r, nm, _ in draws_full[:idx[tr]]]
        if not history:
            continue
        for name, (_, fn) in rec.STRATEGIES.items():
            for _ in range(sets_per):
                nums = fn(history)
                m, rank = grade(nums, actual, bonus)
                res = result[name]
                res["match"] += m
                res["cnt"] += 1
                if rank in (1, 2, 3, 4, 5):
                    res["win5"] += 1
    out = []
    for name, res in result.items():
        c = max(res["cnt"], 1)
        out.append({
            "name": name, "desc": rec.STRATEGIES[name][0],
            "avg": round(res["match"] / c, 3),
            "win5": round(res["win5"] / c * 100, 2),
        })
    out.sort(key=lambda x: -x["avg"])
    _cache[key] = out
    return out


@app.route("/predict")
def predict_page():
    n = min(int(request.args.get("n", 100)), 300)
    bt = run_backtest(n)
    return render_template("predict.html", backtest=bt, n=n)


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
