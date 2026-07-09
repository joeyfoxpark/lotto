package com.lottorie.app

import android.webkit.JavascriptInterface

/** 웹앱(JS) ↔ 광고·결제 브리지. window.AndroidAds 로 노출. */
class AdsBridge(private val activity: MainActivity) {

    @JavascriptInterface
    fun isPremium(): Boolean = Prefs.isPremium(activity)

    /** 보상형 광고 표시. 시청 완료 시 웹의 window.__onAdReward() 호출. */
    @JavascriptInterface
    fun requestReward() {
        activity.runOnUiThread { activity.showRewarded() }
    }

    /** 프리미엄(₩3,000) 구매 플로우 시작. */
    @JavascriptInterface
    fun buyPremium() {
        activity.runOnUiThread { activity.launchPurchase() }
    }
}
