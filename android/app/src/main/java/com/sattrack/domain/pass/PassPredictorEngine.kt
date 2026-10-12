package com.sattrack.domain.pass

import com.sattrack.data.model.ObserverLocation
import com.sattrack.data.model.PassPrediction
import com.sattrack.data.model.SatelliteEntity
import com.sattrack.domain.sgp4.Sgp4Engine
import kotlin.math.*

/**
 * Topocentric Overpass Predictor Engine.
 * Calculates exact Acquisition of Signal (AOS), Peak Culmination Elevation,
 * and Loss of Signal (LOS) look-angles for an observer location.
 */
object PassPredictorEngine {

    data class LookAngles(
        val azimuthDeg: Double,
        val elevationDeg: Double,
        val rangeKm: Double
    )

    fun calculateLookAngles(
        observer: ObserverLocation,
        satLatDeg: Double,
        satLngDeg: Double,
        satAltKm: Double
    ): LookAngles {
        val obsLatRad = Math.toRadians(observer.latDeg)
        val obsLngRad = Math.toRadians(observer.lngDeg)
        val obsR = Sgp4Engine.EARTH_RADIUS_KM + observer.altKm

        val obsX = obsR * cos(obsLatRad) * cos(obsLngRad)
        val obsY = obsR * cos(obsLatRad) * sin(obsLngRad)
        val obsZ = obsR * sin(obsLatRad)

        val satLatRad = Math.toRadians(satLatDeg)
        val satLngRad = Math.toRadians(satLngDeg)
        val satR = Sgp4Engine.EARTH_RADIUS_KM + satAltKm

        val satX = satR * cos(satLatRad) * cos(satLngRad)
        val satY = satR * cos(satLatRad) * sin(satLngRad)
        val satZ = satR * sin(satLatRad)

        val dx = satX - obsX
        val dy = satY - obsY
        val dz = satZ - obsZ
        val range = sqrt(dx * dx + dy * dy + dz * dz)

        // Transform to Topocentric (North, East, Up) frame
        val sinLat = sin(obsLatRad)
        val cosLat = cos(obsLatRad)
        val sinLng = sin(obsLngRad)
        val cosLng = cos(obsLngRad)

        val north = -sinLat * cosLng * dx - sinLat * sinLng * dy + cosLat * dz
        val east = -sinLng * dx + cosLng * dy
        val up = cosLat * cosLng * dx + cosLat * sinLng * dy + sinLat * dz

        val elevationRad = asin(max(-1.0, min(1.0, up / range)))
        var azimuthRad = atan2(east, north)
        if (azimuthRad < 0.0) azimuthRad += 2.0 * PI

        return LookAngles(
            azimuthDeg = Math.toDegrees(azimuthRad),
            elevationDeg = Math.toDegrees(elevationRad),
            rangeKm = range
        )
    }

    /**
     * Scans upcoming 24 hours at 30s increments for passes with elevation >= minElevationDeg
     */
    fun predictPasses(
        sat: SatelliteEntity,
        observer: ObserverLocation,
        minElevationDeg: Double = 10.0,
        maxPasses: Int = 6
    ): List<PassPrediction> {
        val tle = Sgp4Engine.parseTle(sat.line1, sat.line2)
        val now = System.currentTimeMillis()
        val horizonHorizonMs = 86400000L // 24 hours
        val stepMs = 30000L // 30 seconds

        val passes = mutableListOf<PassPrediction>()
        var inPass = false
        var aosTime = 0L
        var aosAzimuth = 0.0
        var maxElev = -90.0
        var maxElevTime = 0L
        var maxAzimuth = 0.0

        var t = now
        val endT = now + horizonHorizonMs

        while (t < endT) {
            val state = Sgp4Engine.propagateTle(sat, tle, t)
            val look = calculateLookAngles(observer, state.latDeg, state.lngDeg, state.altKm)

            if (look.elevationDeg >= minElevationDeg) {
                if (!inPass) {
                    inPass = true
                    aosTime = t
                    aosAzimuth = look.azimuthDeg
                    maxElev = look.elevationDeg
                    maxElevTime = t
                    maxAzimuth = look.azimuthDeg
                } else {
                    if (look.elevationDeg > maxElev) {
                        maxElev = look.elevationDeg
                        maxElevTime = t
                        maxAzimuth = look.azimuthDeg
                    }
                }
            } else if (inPass) {
                // Pass ended (LOS)
                inPass = false
                val losTime = t
                val losAzimuth = look.azimuthDeg
                val durationSec = (losTime - aosTime) / 1000L

                val quality = when {
                    maxElev >= 60.0 -> "EXCELLENT"
                    maxElev >= 30.0 -> "GOOD"
                    else -> "FAIR"
                }

                passes.add(
                    PassPrediction(
                        satId = sat.id,
                        satName = sat.name,
                        aosTimeMs = aosTime,
                        aosAzimuthDeg = round(aosAzimuth * 10.0) / 10.0,
                        maxElevDeg = round(maxElev * 10.0) / 10.0,
                        maxElevTimeMs = maxElevTime,
                        maxAzimuthDeg = round(maxAzimuth * 10.0) / 10.0,
                        losTimeMs = losTime,
                        losAzimuthDeg = round(losAzimuth * 10.0) / 10.0,
                        durationSec = durationSec,
                        quality = quality
                    )
                )

                if (passes.size >= maxPasses) break
            }

            t += stepMs
        }

        return passes
    }

    fun azimuthToCompassDirection(deg: Double): String {
        val directions = arrayOf("N", "NE", "E", "SE", "S", "SW", "W", "NW")
        val index = ((deg / 45.0).roundToInt()) % 8
        return directions[index]
    }
}
