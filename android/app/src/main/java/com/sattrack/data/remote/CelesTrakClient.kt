package com.sattrack.data.remote

import com.sattrack.data.model.SatelliteEntity
import com.sattrack.domain.sgp4.Sgp4Engine
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import java.io.IOException
import java.util.concurrent.TimeUnit

class CelesTrakClient {

    private val httpClient = OkHttpClient.Builder()
        .connectTimeout(12, TimeUnit.SECONDS)
        .readTimeout(15, TimeUnit.SECONDS)
        .build()

    suspend fun fetchGroup(group: String = "stations"): List<SatelliteEntity> = withContext(Dispatchers.IO) {
        val url = "https://celestrak.org/NORAD/elements/gp.php?GROUP=$group&FORMAT=tle"
        val request = Request.Builder().url(url).build()

        try {
            httpClient.newCall(request).execute().use { response ->
                if (!response.isSuccessful) throw IOException("CelesTrak HTTP ${response.code}")
                val body = response.body?.string() ?: return@withContext emptyList()
                parseTleList(body, group)
            }
        } catch (e: Exception) {
            emptyList()
        }
    }

    fun parseTleList(rawText: String, category: String): List<SatelliteEntity> {
        val lines = rawText.lines().map { it.trim() }.filter { it.isNotEmpty() }
        val result = mutableListOf<SatelliteEntity>()

        var i = 0
        while (i + 2 < lines.size) {
            val name = lines[i]
            val l1 = lines[i + 1]
            val l2 = lines[i + 2]

            if (l1.startsWith("1 ") && l2.startsWith("2 ")) {
                try {
                    val tle = Sgp4Engine.parseTle(l1, l2)
                    val id = tle.noradId
                    val incDeg = Math.toDegrees(tle.inclinationRad)
                    val mm = tle.meanMotionRadMin / (2.0 * Math.PI / 1440.0)
                    val a = (Sgp4Engine.MU_EARTH / ((tle.meanMotionRadMin / 60.0).let { it * it })).let { Math.pow(it, 1.0 / 3.0) }
                    val altKm = a - Sgp4Engine.EARTH_RADIUS_KM
                    val periodMin = 1440.0 / mm

                    result.add(
                        SatelliteEntity(
                            id = id,
                            name = name,
                            category = category,
                            intlDesignator = l1.substring(9, 17).trim(),
                            line1 = l1,
                            line2 = l2,
                            orbitType = if (altKm > 35000) "GEO" else if (altKm > 2000) "MEO" else "LEO",
                            inclinationDeg = Math.round(incDeg * 100.0) / 100.0,
                            altitudeKm = Math.round(altKm * 10.0) / 10.0,
                            periodMin = Math.round(periodMin * 10.0) / 10.0,
                            isTracked = false
                        )
                    )
                } catch (_: Exception) {}
                i += 3
            } else {
                i += 1
            }
        }
        return result
    }
}
