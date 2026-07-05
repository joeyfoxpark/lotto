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

    @JavascriptInterface
    fun sendTest(strategy: String) {
        Notif.show(ctx, NumberGen.generate(strategy))
    }
}
