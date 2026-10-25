package com.lottorie.app

import android.content.Context
import android.webkit.JavascriptInterface
import org.json.JSONObject

/** 웹앱(JS) ↔ 네이티브 알림 브리지. window.AndroidNotif 로 노출. */
class NotifBridge(private val ctx: Context) {

    @JavascriptInterface
    fun isSupported(): Boolean = true

    @JavascriptInterface
    fun getSettings(): String {
        val s = NotifScheduler.get(ctx)
        return JSONObject()
            .put("enabled", s.enabled)
            .put("day", s.day)
            .put("hour", s.hour)
            .put("minute", s.minute)
            .put("strategy", s.strategy)
            .toString()
    }

    @JavascriptInterface
    fun save(enabled: Boolean, day: Int, hour: Int, minute: Int, strategy: String) {
        NotifScheduler.save(ctx, NotifScheduler.Settings(enabled, day, hour, minute, strategy))
    }

    /**
     * 웹앱이 계산한 사주 번호표 저장.
     * JSON: {"label":"나","key":"saju:...","nums":{"2026-10-31":[..6개..], ...}}
     */
    @JavascriptInterface
    fun saveSajuNumbers(json: String) {
        NotifScheduler.saveSajuJson(ctx, json)
    }

    @JavascriptInterface
    fun sendTest(strategy: String) {
        val r = RecoNumbers.forStrategy(ctx, strategy)
        Notif.show(ctx, r.nums, r.title, r.note)
    }
}
