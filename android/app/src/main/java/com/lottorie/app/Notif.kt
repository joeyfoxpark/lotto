package com.lottorie.app

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat

/** 알림 채널 생성 + 추천번호 알림 표시. */
object Notif {
    const val CHANNEL = "weekly_reco"
    private const val NOTIF_ID = 1001
    private const val DEFAULT_TITLE = "🍀 이번 주 로또리에 추천번호"

    fun ensureChannel(ctx: Context) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val ch = NotificationChannel(
                CHANNEL, "주간 추천번호", NotificationManager.IMPORTANCE_DEFAULT
            ).apply { description = "매주 정해진 시간에 추천 번호를 알려드려요" }
            ctx.getSystemService(NotificationManager::class.java).createNotificationChannel(ch)
        }
    }

    /**
     * 추천번호 알림.
     * @param title 제목(기본: 패턴 추천 / 사주 번호면 "🔮 ○○님의 이번 주 사주 번호")
     * @param note  본문에 덧붙일 한 줄 안내(선택)
     */
    fun show(ctx: Context, nums: List<Int>, title: String = DEFAULT_TITLE, note: String? = null) {
        ensureChannel(ctx)
        val text = nums.joinToString("   ")
        val launch = ctx.packageManager.getLaunchIntentForPackage(ctx.packageName)
        val pi = PendingIntent.getActivity(
            ctx, 0, launch,
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        )
        val big = StringBuilder(text).append("\n\n")
        if (!note.isNullOrBlank()) big.append(note).append("\n")
        big.append("행운을 빌어요! (재미로 보는 추천입니다)")
        val notif = NotificationCompat.Builder(ctx, CHANNEL)
            .setSmallIcon(R.mipmap.ic_launcher)
            .setContentTitle(title)
            .setContentText(text)
            .setStyle(NotificationCompat.BigTextStyle().bigText(big.toString()))
            .setAutoCancel(true)
            .setContentIntent(pi)
            .build()
        try {
            NotificationManagerCompat.from(ctx).notify(NOTIF_ID, notif)
        } catch (e: SecurityException) {
            // 알림 권한 미허용 시 무시
        }
    }
}
