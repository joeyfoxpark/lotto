package com.lottorie.app

import android.content.Context
import androidx.work.ExistingWorkPolicy
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkManager
import java.util.Calendar
import java.util.concurrent.TimeUnit

/** 주간 추천 알림 스케줄링 (설정 저장 + WorkManager 예약). */
object NotifScheduler {
    private const val PREF = "lottorie_notif"
    private const val WORK = "weekly_reco_work"

    data class Settings(
        val enabled: Boolean,
        val day: Int,        // Calendar.DAY_OF_WEEK (1=일 ~ 7=토)
        val hour: Int,
        val minute: Int,
        val strategy: String
    )

    fun get(ctx: Context): Settings {
        val p = ctx.getSharedPreferences(PREF, Context.MODE_PRIVATE)
        return Settings(
            p.getBoolean("enabled", false),
            p.getInt("day", Calendar.SATURDAY),
            p.getInt("hour", 10),
            p.getInt("minute", 0),
            p.getString("strategy", "balanced") ?: "balanced"
        )
    }

    fun save(ctx: Context, s: Settings) {
        ctx.getSharedPreferences(PREF, Context.MODE_PRIVATE).edit()
            .putBoolean("enabled", s.enabled)
            .putInt("day", s.day)
            .putInt("hour", s.hour)
            .putInt("minute", s.minute)
            .putString("strategy", s.strategy)
            .apply()
        apply(ctx)
    }

    /** 현재 설정으로 다음 알림 예약 (또는 취소). */
    fun apply(ctx: Context) {
        val s = get(ctx)
        val wm = WorkManager.getInstance(ctx)
        wm.cancelUniqueWork(WORK)
        if (!s.enabled) return
        enqueue(ctx, delayToNext(s.day, s.hour, s.minute, skipImminent = false))
    }

    /** 알림 발송 후 다음 주 재예약. */
    fun scheduleNext(ctx: Context) {
        val s = get(ctx)
        if (!s.enabled) return
        enqueue(ctx, delayToNext(s.day, s.hour, s.minute, skipImminent = true))
    }

    private fun enqueue(ctx: Context, delayMs: Long) {
        val req = OneTimeWorkRequestBuilder<RecoWorker>()
            .setInitialDelay(delayMs, TimeUnit.MILLISECONDS)
            .build()
        WorkManager.getInstance(ctx).enqueueUniqueWork(WORK, ExistingWorkPolicy.REPLACE, req)
    }

    private fun delayToNext(day: Int, hour: Int, minute: Int, skipImminent: Boolean): Long {
        val now = Calendar.getInstance()
        val next = Calendar.getInstance().apply {
            set(Calendar.DAY_OF_WEEK, day)
            set(Calendar.HOUR_OF_DAY, hour)
            set(Calendar.MINUTE, minute)
            set(Calendar.SECOND, 0)
            set(Calendar.MILLISECOND, 0)
        }
        // 이미 지났거나(재예약 시 1분 이내면) 다음 주로
        while (next.timeInMillis <= now.timeInMillis ||
            (skipImminent && next.timeInMillis - now.timeInMillis < 60_000)
        ) {
            next.add(Calendar.WEEK_OF_YEAR, 1)
        }
        return next.timeInMillis - now.timeInMillis
    }
}
