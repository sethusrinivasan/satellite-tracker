package com.sattrack

import com.sattrack.data.model.SatelliteEntity
import com.sattrack.domain.sgp4.Sgp4Engine
import org.junit.Assert.*
import org.junit.Test

class Sgp4EngineTest {

    private val issSample = SatelliteEntity(
        id = 25544,
        name = "ISS (ZARYA)",
        category = "stations",
        line1 = "1 25544U 98067A   24095.53472222  .00016717  00000-0  10270-3 0  9002",
        line2 = "2 25544  51.6416 247.4627 0006703 130.5360 325.0288 15.49887754447413"
    )

    @Test
    fun testParseTle() {
        val tle = Sgp4Engine.parseTle(issSample.line1, issSample.line2)
        assertEquals(25544, tle.noradId)
        assertEquals(2024, tle.epochYear)
        assertEquals(51.6416, Math.toDegrees(tle.inclinationRad), 0.001)
        assertEquals(0.0006703, tle.eccentricity, 0.000001)
    }

    @Test
    fun testPropagateISS() {
        val now = 1712284800000L // 2024-04-05 00:00:00 UTC
        val state = Sgp4Engine.propagate(issSample, now)

        assertEquals(25544, state.id)
        assertEquals("ISS (ZARYA)", state.name)
        assertTrue("Altitude should be between 390 and 440 km for ISS", state.altKm in 390.0..440.0)
        assertTrue("Velocity should be ~7.6 km/s for LEO", state.velKmS in 7.0..8.2)
        assertTrue("Footprint radius should be between 2000 and 2600 km", state.footprintKm in 2000.0..2600.0)
        assertEquals("LEO", state.orbitType)
    }

    @Test
    fun testGroundTrackGeneration() {
        val track = Sgp4Engine.computeGroundTrack(issSample, durationMin = 90, stepMin = 5)
        assertTrue("Ground track should have at least 1 segment", track.isNotEmpty())
        val totalPoints = track.sumOf { it.size }
        assertTrue("Should have calculated multiple trajectory points", totalPoints >= 15)
    }
}
