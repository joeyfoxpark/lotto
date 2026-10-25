package com.lottorie.app

import android.content.Context
import org.json.JSONObject
import java.util.Calendar
import java.util.Locale

/**
 * 알림에 넣을 번호 결정.
 *  - "hot" / "balanced" / "random"  → NumberGen(패턴 축약판)
 *  - "saju:<사주키>"                → 웹앱이 미리 계산해 넘겨준 주차별 사주 번호표에서
 *                                     다가오는 토요일(추첨일) 번호를 꺼냄. 없으면 균형 번호로 대체.
 */
object RecoNumbers {
    data class Reco(val title: String, val nums: List<Int>, val note: String?)

    private const val DEFAULT_TITLE = "🍀 이번 주 로또리에 추천번호"

    fun forStrategy(ctx: Context, strategy: String): Reco {
        if (!strategy.startsWith("saju")) {
            return Reco(DEFAULT_TITLE, NumberGen.generate(strategy), null)
        }
        val json = NotifScheduler.getSajuJson(ctx)
        if (json != null) {
            try {
                val o = JSONObject(json)
                if (!o.has("key") || o.getString("key") == strategy) {
                    val table = o.getJSONObject("nums")
                    val key = nextSaturdayIso()
                    if (table.has(key)) {
                        val arr = table.getJSONArray(key)
                        val nums = (0 until arr.length()).map { arr.getInt(it) }
                        if (nums.size == 6) {
                            val label = o.optString("label", "")
                            val who = if (label.isNotBlank()) "${label}님의 " else "내 "
                            return Reco("🔮 ${who}이번 주 사주 번호", nums, "추첨일 ${key}의 기운을 반영한 번호예요")
                        }
                    }
                }
            } catch (e: Exception) {
            }
        }
        // 번호표가 없거나 기간이 지남 → 균형 번호 + 안내
        return Reco(
            DEFAULT_TITLE, NumberGen.generate("balanced"),
            "사주 번호를 다시 받으려면 앱을 한 번 열어주세요"
        )
    }

    /** 오늘 포함 다가오는 토요일 yyyy-MM-dd (웹앱 nextSaturday()와 동일 규칙, 기기 로컬 날짜). */
    fun nextSaturdayIso(): String {
        val c = Calendar.getInstance()
        val ahead = (Calendar.SATURDAY - c.get(Calendar.DAY_OF_WEEK) + 7) % 7
        c.add(Calendar.DAY_OF_MONTH, ahead)
        return String.format(
            Locale.US, "%04d-%02d-%02d",
            c.get(Calendar.YEAR), c.get(Calendar.MONTH) + 1, c.get(Calendar.DAY_OF_MONTH)
        )
    }
}
