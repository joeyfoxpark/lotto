package com.lottorie.app

import kotlin.random.Random

/** 알림용 추천 번호 생성 (웹앱 전략의 축약판). */
object NumberGen {
    // 1~45 전체 출현 빈도 (index 0 = 1번)
    private val FREQ = intArrayOf(
        169, 154, 172, 162, 153, 165, 168, 158, 136, 161, 165, 178, 179, 172, 167,
        168, 171, 176, 168, 169, 166, 144, 147, 165, 152, 165, 181, 157, 155, 158,
        168, 144, 174, 184, 162, 163, 172, 170, 167, 172, 150, 157, 163, 164, 175
    )

    fun generate(strategy: String): List<Int> = when (strategy) {
        "hot" -> weighted { n -> Math.pow(FREQ[n - 1].toDouble(), 2.0) }
        "random" -> random6()
        else -> balanced()
    }

    private fun random6(): List<Int> {
        val s = sortedSetOf<Int>()
        while (s.size < 6) s.add(Random.nextInt(1, 46))
        return s.toList()
    }

    private fun band(n: Int) = if (n <= 40) (n - 1) / 10 else 4

    private fun realistic(nums: List<Int>): Boolean {
        val s = nums.sorted()
        val sum = s.sum()
        if (sum !in 100..175) return false
        val odd = s.count { it % 2 == 1 }
        if (odd == 0 || odd == 6) return false
        if (s.map { band(it) }.toSet().size < 3) return false
        for (i in 0..3) if (s[i] + 1 == s[i + 1] && s[i + 1] + 1 == s[i + 2]) return false
        return true
    }

    private fun balanced(): List<Int> {
        repeat(3000) {
            val c = random6()
            if (realistic(c)) return c
        }
        return random6()
    }

    private fun weighted(w: (Int) -> Double): List<Int> {
        val chosen = sortedSetOf<Int>()
        while (chosen.size < 6) {
            var total = 0.0
            for (n in 1..45) if (n !in chosen) total += w(n)
            var r = Random.nextDouble() * total
            for (n in 1..45) {
                if (n in chosen) continue
                r -= w(n)
                if (r <= 0) { chosen.add(n); break }
            }
        }
        return chosen.toList()
    }
}
