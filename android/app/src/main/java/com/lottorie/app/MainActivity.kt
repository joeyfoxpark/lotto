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
import android.webkit.WebResourceResponse
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.activity.OnBackPressedCallback
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.webkit.WebViewAssetLoader
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

    // 웹앱은 앱에 동봉된 HTML(오프라인 가능)을 로컬 오리진으로 띄우고,
    // SiteUpdater 가 GitHub Pages 최신본을 백그라운드로 받아 자동 갱신한다.
    private val localHost = WebViewAssetLoader.DEFAULT_DOMAIN   // appassets.androidplatform.net
    private val startUrl = "https://$localHost/app/index.html"
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
        webView.addJavascriptInterface(AppBridge(this), "AndroidApp")

        // 로컬 HTML 제공: 내부 저장소 갱신본 → 없으면 assets 동봉본
        val assetLoader = WebViewAssetLoader.Builder()
            .setDomain(localHost)
            .addPathHandler("/app/", LocalSiteHandler(this))
            .build()

        webView.webChromeClient = WebChromeClient()
        webView.webViewClient = object : WebViewClient() {
            override fun shouldInterceptRequest(
                view: WebView, request: WebResourceRequest
            ): WebResourceResponse? = assetLoader.shouldInterceptRequest(request.url)

            override fun shouldOverrideUrlLoading(view: WebView, request: WebResourceRequest): Boolean {
                val host = request.url.host ?: ""
                return if (host == localHost || host.contains(siteHost)) {
                    false
                } else {
                    startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(request.url.toString())))
                    true
                }
            }
        }

        if (savedInstanceState == null) {
            webView.loadUrl(startUrl)
        } else {
            webView.restoreState(savedInstanceState)
        }

        // 최신 회차 데이터(사이트 최신본) 백그라운드 확인 → 받으면 웹에 '새로고침' 배너 표시
        SiteUpdater.checkAsync(this) {
            runOnUiThread {
                webView.evaluateJavascript("window.__onSiteUpdated && window.__onSiteUpdated();", null)
            }
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

    // ------------------------ 공유 ------------------------
    /** 번호 텍스트를 안드로이드 공유 시트로 보낸다(카카오톡·문자 등). */
    fun shareText(text: String) {
        val send = Intent(Intent.ACTION_SEND).apply {
            type = "text/plain"
            putExtra(Intent.EXTRA_TEXT, text)
        }
        try {
            startActivity(Intent.createChooser(send, "번호 공유"))
        } catch (e: Exception) {
            // 공유 가능한 앱이 없는 경우 무시
        }
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
