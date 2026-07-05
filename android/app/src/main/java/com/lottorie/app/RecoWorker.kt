package com.lottorie.app

import android.content.Context
import androidx.work.Worker
import androidx.work.WorkerParameters

/** 예약 시각에 실행: 번호 생성 → 알림 → 다음 주 재예약. */
class RecoWorker(ctx: Context, params: WorkerParameters) : Worker(ctx, params) {
    override fun doWork(): Result {
        val s = NotifScheduler.get(applicationContext)
        if (s.enabled) {
            val nums = NumberGen.generate(s.strategy)
            Notif.show(applicationContext, nums)
        }
        NotifScheduler.scheduleNext(applicationContext)
        return Result.success()
    }
}
