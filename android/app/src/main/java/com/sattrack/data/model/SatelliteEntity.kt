package com.sattrack.data.model

data class SatelliteEntity(
    val id: Int,
    val name: String,
    val category: String,
    val intlDesignator: String = "",
    val line1: String,
    val line2: String,
    val orbitType: String = "LEO",
    val inclinationDeg: Double = 0.0,
    val altitudeKm: Double = 400.0,
    val periodMin: Double = 90.0,
    val isTracked: Boolean = false,
    val colorHex: String = "#38BDF8"
)

data class SatelliteState(
    val id: Int,
    val name: String,
    val latDeg: Double,
    val lngDeg: Double,
    val altKm: Double,
    val velKmS: Double,
    val velMph: Double,
    val footprintKm: Double,
    val inclinationDeg: Double,
    val periodMin: Double,
    val orbitType: String,
    val colorHex: String,
    val timestampMs: Long = System.currentTimeMillis()
)

data class ObserverLocation(
    val latDeg: Double = 37.7749,
    val lngDeg: Double = -122.4194,
    val altKm: Double = 0.03,
    val name: String = "Observer (Default)"
)

data class PassPrediction(
    val satId: Int,
    val satName: String,
    val aosTimeMs: Long,
    val aosAzimuthDeg: Double,
    val maxElevDeg: Double,
    val maxElevTimeMs: Long,
    val maxAzimuthDeg: Double,
    val losTimeMs: Long,
    val losAzimuthDeg: Double,
    val durationSec: Long,
    val quality: String // EXCELLENT, GOOD, FAIR
)
