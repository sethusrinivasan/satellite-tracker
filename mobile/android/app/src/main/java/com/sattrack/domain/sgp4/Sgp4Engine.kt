package com.sattrack.domain.sgp4

import com.sattrack.data.model.SatelliteEntity
import com.sattrack.data.model.SatelliteState
import kotlin.math.*

/**
 * High-performance, self-contained SGP4 / Keplerian Orbital Propagation Engine.
 * Converts Two-Line Element (TLE) records to WGS-84 Geodetic coordinates (Lat, Lng, Alt, Velocity)
 * from first principles with zero external dependencies.
 */
object Sgp4Engine {

    const val EARTH_RADIUS_KM = 6378.137
    const val MU_EARTH = 398600.4418 // km^3 / s^2
    const val J2 = 1.08262668e-3
    const val WGS84_FLATTENING = 1.0 / 298.257223563

    data class TleRecord(
        val noradId: Int,
        val epochYear: Int,
        val epochDay: Double,
        val bStar: Double,
        val inclinationRad: Double,
        val raanRad: Double,
        val eccentricity: Double,
        val argPerigeeRad: Double,
        val meanAnomalyRad: Double,
        val meanMotionRadMin: Double,
        val revAtEpoch: Int
    )

    fun parseTle(line1: String, line2: String): TleRecord {
        val l1 = line1.trim()
        val l2 = line2.trim()

        val noradId = l1.substring(2, 7).trim().toIntOrNull() ?: 0
        val epochYearRaw = l1.substring(18, 20).trim().toIntOrNull() ?: 24
        val epochYear = if (epochYearRaw < 57) 2000 + epochYearRaw else 1900 + epochYearRaw
        val epochDay = l1.substring(20, 32).trim().toDoubleOrNull() ?: 1.0

        val bStarStr = l1.substring(53, 61).trim().replace(" ", "")
        val bStar = parseExponentialNotation(bStarStr)

        val incDeg = l2.substring(8, 16).trim().toDoubleOrNull() ?: 0.0
        val raanDeg = l2.substring(17, 25).trim().toDoubleOrNull() ?: 0.0
        val eccStr = "0." + l2.substring(26, 33).trim()
        val ecc = eccStr.toDoubleOrNull() ?: 0.001
        val argPerDeg = l2.substring(34, 42).trim().toDoubleOrNull() ?: 0.0
        val meanAnomDeg = l2.substring(43, 51).trim().toDoubleOrNull() ?: 0.0
        val mmRevsDay = l2.substring(52, 63).trim().toDoubleOrNull() ?: 15.0
        val revEpoch = l2.substring(63, 68).trim().toIntOrNull() ?: 0

        val mmRadMin = mmRevsDay * (2.0 * PI / 1440.0)

        return TleRecord(
            noradId = noradId,
            epochYear = epochYear,
            epochDay = epochDay,
            bStar = bStar,
            inclinationRad = Math.toRadians(incDeg),
            raanRad = Math.toRadians(raanDeg),
            eccentricity = ecc,
            argPerigeeRad = Math.toRadians(argPerDeg),
            meanAnomalyRad = Math.toRadians(meanAnomDeg),
            meanMotionRadMin = mmRadMin,
            revAtEpoch = revEpoch
        )
    }

    private fun parseExponentialNotation(s: String): Double {
        if (s.isEmpty() || s == "0") return 0.0
        try {
            val sign = if (s.startsWith("-")) -1.0 else 1.0
            val clean = s.removePrefix("-").removePrefix("+")
            if (clean.length >= 2) {
                val mantissa = clean.substring(0, clean.length - 2).toDoubleOrNull() ?: return 0.0
                val exp = clean.substring(clean.length - 2).toIntOrNull() ?: 0
                return sign * (mantissa * 1e-5) * 10.0.pow(exp)
            }
        } catch (_: Exception) {}
        return 0.0
    }

    /**
     * Propagate satellite to timestamp ms and return Geodetic coordinates
     */
    fun propagate(sat: SatelliteEntity, targetMs: Long = System.currentTimeMillis()): SatelliteState {
        val tle = parseTle(sat.line1, sat.line2)
        return propagateTle(sat, tle, targetMs)
    }

    fun propagateTle(sat: SatelliteEntity, tle: TleRecord, targetMs: Long): SatelliteState {
        // Julian date at target
        val jdTarget = timestampToJulianDate(targetMs)
        // Julian date at epoch
        val jdEpoch = epochToJulianDate(tle.epochYear, tle.epochDay)
        val deltaMin = (jdTarget - jdEpoch) * 1440.0

        // Semi-major axis from mean motion
        // n in rad/s = meanMotionRadMin / 60
        val nSec = tle.meanMotionRadMin / 60.0
        val a = (MU_EARTH / (nSec * nSec)).pow(1.0 / 3.0)

        // J2 Secular perturbations
        val p = a * (1.0 - tle.eccentricity * tle.eccentricity)
        val cosInc = cos(tle.inclinationRad)
        val sinInc = sin(tle.inclinationRad)

        val j2Factor = 1.5 * J2 * (EARTH_RADIUS_KM / p).pow(2.0) * tle.meanMotionRadMin
        val raanRate = -j2Factor * cosInc // rad/min
        val argPerRate = 0.75 * j2Factor * (5.0 * cosInc * cosInc - 1.0) // rad/min

        // Updated orbital elements
        val raan = (tle.raanRad + raanRate * deltaMin) % (2.0 * PI)
        val argPer = (tle.argPerigeeRad + argPerRate * deltaMin) % (2.0 * PI)
        val meanAnom = (tle.meanAnomalyRad + tle.meanMotionRadMin * deltaMin) % (2.0 * PI)

        // Solve Kepler's equation for eccentric anomaly: M = E - e * sin(E)
        var eAnom = meanAnom
        for (i in 0..15) {
            val f = eAnom - tle.eccentricity * sin(eAnom) - meanAnom
            val fPrime = 1.0 - tle.eccentricity * cos(eAnom)
            val delta = f / fPrime
            eAnom -= delta
            if (abs(delta) < 1e-8) break
        }

        // True anomaly
        val sinNu = (sqrt(1.0 - tle.eccentricity * tle.eccentricity) * sin(eAnom)) / (1.0 - tle.eccentricity * cos(eAnom))
        val cosNu = (cos(eAnom) - tle.eccentricity) / (1.0 - tle.eccentricity * cos(eAnom))
        val nu = atan2(sinNu, cosNu)

        // Radial distance
        val r = a * (1.0 - tle.eccentricity * cos(eAnom))

        // Position in orbital plane
        val u = (argPer + nu) % (2.0 * PI) // Argument of latitude
        val xOrb = r * cos(u)
        val yOrb = r * sin(u)

        // Transform to ECI coordinates (TEME)
        val cosRaan = cos(raan)
        val sinRaan = sin(raan)

        val xEci = xOrb * cosRaan - yOrb * cosInc * sinRaan
        val yEci = xOrb * sinRaan + yOrb * cosInc * cosRaan
        val zEci = yOrb * sinInc

        // Orbital Velocity
        val velKmS = sqrt(MU_EARTH * (2.0 / r - 1.0 / a))
        val velMph = velKmS * 2236.936

        // GMST (Greenwich Mean Sidereal Time)
        val gmst = computeGmst(jdTarget)

        // ECI to ECEF (Rotate by GMST)
        val cosGmst = cos(gmst)
        val sinGmst = sin(gmst)

        val xEcf = xEci * cosGmst + yEci * sinGmst
        val yEcf = -xEci * sinGmst + yEci * cosGmst
        val zEcf = zEci

        // ECEF to Geodetic Coordinates (WGS-84)
        val lngRad = atan2(yEcf, xEcf)
        val pDist = sqrt(xEcf * xEcf + yEcf * yEcf)
        var latRad = atan2(zEcf, pDist * (1.0 - WGS84_FLATTENING))

        for (i in 0..5) {
            val sinLat = sin(latRad)
            val nRadius = EARTH_RADIUS_KM / sqrt(1.0 - (2.0 * WGS84_FLATTENING - WGS84_FLATTENING * WGS84_FLATTENING) * sinLat * sinLat)
            latRad = atan2(zEcf + (2.0 * WGS84_FLATTENING - WGS84_FLATTENING * WGS84_FLATTENING) * nRadius * sinLat, pDist)
        }

        val latDeg = Math.toDegrees(latRad)
        val lngDeg = (Math.toDegrees(lngRad) + 180.0) % 360.0 - 180.0
        val altKm = r - EARTH_RADIUS_KM

        // Footprint radius on Earth surface
        val footprintAngle = acos(min(1.0, EARTH_RADIUS_KM / (EARTH_RADIUS_KM + max(10.0, altKm))))
        val footprintKm = EARTH_RADIUS_KM * footprintAngle

        val periodMin = (2.0 * PI * a.pow(1.5)) / (sqrt(MU_EARTH) * 60.0)

        return SatelliteState(
            id = sat.id,
            name = sat.name,
            latDeg = round(latDeg * 100.0) / 100.0,
            lngDeg = round(lngDeg * 100.0) / 100.0,
            altKm = round(altKm * 10.0) / 10.0,
            velKmS = round(velKmS * 100.0) / 100.0,
            velMph = round(velMph),
            footprintKm = round(footprintKm),
            inclinationDeg = round(Math.toDegrees(tle.inclinationRad) * 100.0) / 100.0,
            periodMin = round(periodMin * 10.0) / 10.0,
            orbitType = if (altKm > 35000) "GEO" else if (altKm > 2000) "MEO" else "LEO",
            colorHex = sat.colorHex,
            timestampMs = targetMs
        )
    }

    /**
     * Computes future ground track points for map polyline rendering
     */
    fun computeGroundTrack(sat: SatelliteEntity, durationMin: Int = 90, stepMin: Int = 2): List<List<Pair<Double, Double>>> {
        val now = System.currentTimeMillis()
        val tle = parseTle(sat.line1, sat.line2)
        val segments = mutableListOf<MutableList<Pair<Double, Double>>>()
        segments.add(mutableListOf())

        var lastLng: Double? = null

        for (m in -10..durationMin step stepMin) {
            val t = now + m * 60000L
            val state = propagateTle(sat, tle, t)
            val lng = state.lngDeg

            if (lastLng != null && abs(lng - lastLng) > 180.0) {
                // Crossed antimeridian (+180 / -180) -> split into separate segment
                segments.add(mutableListOf())
            }
            segments.last().add(Pair(state.latDeg, lng))
            lastLng = lng
        }

        return segments.filter { it.size >= 2 }
    }

    fun timestampToJulianDate(timeMs: Long): Double {
        return timeMs / 86400000.0 + 2440587.5
    }

    fun epochToJulianDate(year: Int, dayOfYear: Double): Double {
        var y = year - 1
        val a = y / 100
        val b = 2 - a + a / 4
        val jd0 = (365.25 * (y + 4716)).toInt() + (30.6001 * 14).toInt() + 1720994.5 + b
        return jd0 + dayOfYear
    }

    fun computeGmst(jd: Double): Double {
        val d = jd - 2451545.0
        var gmst = 280.46061837 + 360.98564736629 * d
        gmst = Math.toRadians((gmst % 360.0 + 360.0) % 360.0)
        return gmst
    }
}
