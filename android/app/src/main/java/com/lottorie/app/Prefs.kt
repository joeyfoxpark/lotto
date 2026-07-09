package com.lottorie.app

import android.content.Context

/** 프리미엄(광고 제거) 상태 저장. */
object Prefs {
    private const val PREF = "lottorie_premium"

    fun isPremium(ctx: Context): Boolean =
        ctx.getSharedPreferences(PREF, Context.MODE_PRIVATE).getBoolean("premium", false)

    fun setPremium(ctx: Context, value: Boolean) {
        ctx.getSharedPreferences(PREF, Context.MODE_PRIVATE)
            .edit().putBoolean("premium", value).apply()
    }
}
