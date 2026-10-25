package com.lottorie.app

import android.webkit.JavascriptInterface

/** 웹앱(JS) ↔ 앱 공통 브리지. window.AndroidApp 로 노출. */
class AppBridge(private val activity: MainActivity) {

    /** 번호 공유(안드로이드 공유 시트: 카카오톡·문자 등). */
    @JavascriptInterface
    fun share(text: String) {
        activity.runOnUiThread { activity.shareText(text) }
    }

    @JavascriptInterface
    fun version(): String = BuildConfig.VERSION_NAME

    /** 현재 로드된 웹앱의 빌드 스탬프(디버그 표시용). */
    @JavascriptInterface
    fun siteStamp(): String = SiteUpdater.currentStamp(activity)
}
