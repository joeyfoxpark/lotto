package com.lottorie.app

import android.content.Context
import android.webkit.WebResourceResponse
import androidx.webkit.WebViewAssetLoader
import java.io.File
import java.io.FileInputStream
import java.io.InputStream
import java.net.HttpURLConnection
import java.net.URL

/**
 * 웹앱 HTML 동봉 + 자동 갱신.
 *
 *  - 앱 설치본(assets/index.html)을 기본으로 띄워 인터넷 없이도 즉시 실행된다.
 *  - 실행 때마다 백그라운드로 GitHub Pages 최신본을 받아 빌드 스탬프가 더 새것이면
 *    내부 저장소(files/site/)에 저장하고 웹에 알린다(window.__onSiteUpdated → 새로고침 배너).
 *  - 다음 실행부터는 내부 저장소 사본이 우선 사용된다.
 *
 *  빌드 스탬프: <meta name="lottorie-build" content="UTC시각|최신회차"> (web_static/build_html.py 가 기록)
 */
object SiteUpdater {
    const val REMOTE = "https://joeyfoxpark.github.io/lotto/"
    private val STAMP = Regex("name=\"lottorie-build\" content=\"([^\"]*)\"")

    fun siteDir(ctx: Context): File = File(ctx.filesDir, "site")

    fun stampOf(html: String): String = STAMP.find(html)?.groupValues?.get(1) ?: ""

    /** 현재 사용 중인 사본(내부 저장소 우선, 없으면 assets)의 스탬프. */
    fun currentStamp(ctx: Context): String {
        return try {
            val f = File(siteDir(ctx), "index.html")
            val head = if (f.exists()) readHead(FileInputStream(f)) else readHead(ctx.assets.open("index.html"))
            stampOf(head)
        } catch (e: Exception) {
            ""
        }
    }

    private fun readHead(stream: InputStream): String = stream.bufferedReader(Charsets.UTF_8).use { r ->
        val buf = CharArray(4000)
        val n = r.read(buf)
        if (n > 0) String(buf, 0, n) else ""
    }

    /** 스탬프 앞부분(UTC 시각)이 더 크면 새 버전. */
    fun isNewer(remote: String, local: String): Boolean {
        if (remote.isEmpty()) return false
        if (local.isEmpty()) return true
        return remote.substringBefore('|') > local.substringBefore('|')
    }

    /** 백그라운드 갱신 확인. 새 버전을 저장했으면 onUpdated 호출(워커 스레드에서 호출됨). */
    fun checkAsync(ctx: Context, onUpdated: () -> Unit) {
        val app = ctx.applicationContext
        val t = Thread {
            try {
                val html = fetch(REMOTE + "index.html")
                if (html != null) {
                    val remote = stampOf(html)
                    if (isNewer(remote, currentStamp(app))) {
                        val dir = siteDir(app)
                        dir.mkdirs()
                        // 개인정보처리방침도 같이(실패해도 기존/동봉본 유지)
                        val privacyFile = File(dir, "privacy.html")
                        val privacy = fetch(REMOTE + "privacy.html")
                        if (privacy != null) {
                            privacyFile.writeText(privacy)
                        } else if (!privacyFile.exists()) {
                            copyAsset(app, "privacy.html", privacyFile)
                        }
                        // index.html 은 임시 파일에 쓴 뒤 교체(중간 상태 방지)
                        val tmp = File(dir, "index.html.tmp")
                        tmp.writeText(html)
                        val dst = File(dir, "index.html")
                        if (!tmp.renameTo(dst)) {
                            dst.writeText(html)
                            tmp.delete()
                        }
                        onUpdated()
                    }
                }
            } catch (e: Exception) {
                // 오프라인/서버 오류 — 조용히 무시(다음 실행 때 재시도)
            }
        }
        t.isDaemon = true
        t.start()
    }

    private fun copyAsset(ctx: Context, name: String, dst: File) {
        try {
            ctx.assets.open(name).use { i -> dst.outputStream().use { o -> i.copyTo(o) } }
        } catch (e: Exception) {
        }
    }

    private fun fetch(url: String): String? {
        val c = URL(url).openConnection() as HttpURLConnection
        return try {
            c.connectTimeout = 10_000
            c.readTimeout = 20_000
            c.setRequestProperty("Cache-Control", "no-cache")
            c.setRequestProperty("User-Agent", "Lottorie-Android/" + BuildConfig.VERSION_NAME)
            if (c.responseCode == 200) c.inputStream.bufferedReader(Charsets.UTF_8).use { it.readText() } else null
        } finally {
            c.disconnect()
        }
    }
}

/**
 * https://appassets.androidplatform.net/app/<파일> 요청을 로컬 파일로 응답.
 * 내부 저장소 사본(갱신본)이 있으면 그것을, 없으면 assets 동봉본을 준다.
 * 항상 같은 URL/오리진을 쓰므로 localStorage(저장된 사주·내 번호 기록)가 유지된다.
 */
class LocalSiteHandler(private val ctx: Context) : WebViewAssetLoader.PathHandler {
    override fun handle(path: String): WebResourceResponse? {
        var name = path.trimStart('/')
        if (name.isEmpty()) name = "index.html"
        if (name.contains("..")) return null
        val stream: InputStream = try {
            val f = File(SiteUpdater.siteDir(ctx), name)
            if (f.exists()) FileInputStream(f) else ctx.assets.open(name)
        } catch (e: Exception) {
            return null
        }
        val mime = when {
            name.endsWith(".html") -> "text/html"
            name.endsWith(".png") -> "image/png"
            name.endsWith(".js") -> "application/javascript"
            name.endsWith(".css") -> "text/css"
            name.endsWith(".json") -> "application/json"
            else -> "application/octet-stream"
        }
        val res = WebResourceResponse(mime, "utf-8", stream)
        res.responseHeaders = mapOf("Cache-Control" to "no-cache")
        return res
    }
}
