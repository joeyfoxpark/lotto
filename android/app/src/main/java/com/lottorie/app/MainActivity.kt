package com.lottorie.app

import android.Manifest
import android.annotation.SuppressLint
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.view.View
import android.webkit.WebChromeClient
import android.webkit.WebResourceRequest
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.activity.OnBackPressedCallback
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import com.google.android.gms.ads.AdRequest
import com.google.android.gms.ads.AdView
import com.google.android.gms.ads.LoadAdError
import com.google.android.gms.ads.MobileAds
import com.google.android.gms.ads.rewarded.RewardedAd
import com.google.android.gms.ads.rewarded.RewardedAdLoadCallback

class MainActivity : AppCompatActivity() {

    private lateinit var webView: WebView
    private lateinit var adView: AdView
    private lateinit var billing: BillingManager
    private var rewardedAd: RewardedAd? = null

    private val siteUrl = "https://joeyfoxpark.github.io/lotto/"
    private val siteHost = "joeyfoxpark.github.io"

    // 디버그=테스트 광고 / 릴리스=실제 광고 (build.gradle에서 주입)
    private val rewardedAdUnit = BuildConfig.ADMOB_REWARDED_ID

    private val requestNotifPermission =
        registerForActivityResult(ActivityResultContracts.RequestPermission()) { }

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        // 알림 채널 준비 + 권한 요청(Android 13+)
        Notif.ensureChannel(this)
        maybeRequestNotifPermission()

        // 인앱결제 (프리미엄 = 광고 제거)
        billing = BillingManager(this) { runOnUiThread { applyPremium() } }
        billing.start()

        // 애드몹: 배너 + 보상형 미리 로드 (프리미엄이면 배너 숨김)
        MobileAds.initialize(this) {}
        adView = findViewById(R.id.adView)
        if (Prefs.isPremium(this)) {
            adView.visibility = View.GONE
        } else {
            adView.loadAd(AdRequest.Builder().build())
            loadRewarded()
        }

        webView = findViewById(R.id.webView)
        webView.settings.apply {
            javaScriptEnabled = true
            domStorageEnabled = true
            cacheMode = android.webkit.WebSettings.LOAD_DEFAULT
        }
        // 웹앱 ↔ 네이티브 브리지
        webView.addJavascriptInterface(NotifBridge(this), "AndroidNotif")
        webView.addJavascriptInterface(AdsBridge(this), "AndroidAds")

        webView.webChromeClient = WebChromeClient()
        webView.webViewClient = object : WebViewClient() {
            override fun shouldOverrideUrlLoading(view: WebView, request: WebResourceRequest): Boolean {
                val url = request.url.toString()
                return if (request.url.host?.contains(siteHost) == true) {
                    false
                } else {
                    startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
                    true
                }
            }
        }

        if (savedInstanceState == null) {
            webView.loadUrl(siteUrl)
        } else {
            webView.restoreState(savedInstanceState)
        }

        onBackPressedDispatcher.addCallback(this, object : OnBackPressedCallback(true) {
            override fun handleOnBackPressed() {
                if (webView.canGoBack()) {
                    webView.goBack()
                } else {
                    isEnabled = false
                    onBackPressedDispatcher.onBackPressed()
                }
            }
        })
    }

    // ------------------------ 보상형 광고 ------------------------
    private fun loadRewarded() {
        RewardedAd.load(this, rewardedAdUnit, AdRequest.Builder().build(),
            object : RewardedAdLoadCallback() {
                override fun onAdLoaded(ad: RewardedAd) { rewardedAd = ad }
                override fun onAdFailedToLoad(err: LoadAdError) { rewardedAd = null }
            })
    }

    /** 사주 추천 잠금해제용 보상형 광고. 시청 완료 → 웹 콜백. */
    fun showRewarded() {
        if (Prefs.isPremium(this)) { notifyReward(); return }
        val ad = rewardedAd
        if (ad == null) {
            // 광고 로드 실패(네트워크 등) 시 기능을 막지 않고 통과시킨다 (UX 우선)
            notifyReward()
            loadRewarded()
            return
        }
        rewardedAd = null
        ad.show(this) { notifyReward() }
        loadRewarded() // 다음 광고 미리 로드
    }

    private fun notifyReward() {
        webView.evaluateJavascript("window.__onAdReward && window.__onAdReward();", null)
    }

    // ------------------------ 프리미엄(결제) ------------------------
    fun launchPurchase() = billing.launchPurchase(this)

    private fun applyPremium() {
        if (!Prefs.isPremium(this)) return
        adView.visibility = View.GONE
        webView.evaluateJavascript("window.__onPremium && window.__onPremium();", null)
    }

    override fun onSaveInstanceState(outState: Bundle) {
        super.onSaveInstanceState(outState)
        webView.saveState(outState)
    }

    private fun maybeRequestNotifPermission() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            val granted = ContextCompat.checkSelfPermission(
                this, Manifest.permission.POST_NOTIFICATIONS
            ) == PackageManager.PERMISSION_GRANTED
            if (!granted) requestNotifPermission.launch(Manifest.permission.POST_NOTIFICATIONS)
        }
    }
}
