package com.sattrack

import com.sattrack.data.model.ObserverLocation
import com.sattrack.domain.pass.PassPredictorEngine
import org.junit.Assert.*
import org.junit.Test

class PassPredictorTest {

    @Test
    fun testCompassDirections() {
        assertEquals("N", PassPredictorEngine.azimuthToCompassDirection(0.0))
        assertEquals("NE", PassPredictorEngine.azimuthToCompassDirection(45.0))
        assertEquals("E", PassPredictorEngine.azimuthToCompassDirection(90.0))
        assertEquals("SE", PassPredictorEngine.azimuthToCompassDirection(135.0))
        assertEquals("S", PassPredictorEngine.azimuthToCompassDirection(180.0))
        assertEquals("SW", PassPredictorEngine.azimuthToCompassDirection(225.0))
        assertEquals("W", PassPredictorEngine.azimuthToCompassDirection(270.0))
        assertEquals("NW", PassPredictorEngine.azimuthToCompassDirection(315.0))
    }

    @Test
    fun testZenithLookAngle() {
        val observer = ObserverLocation(latDeg = 0.0, lngDeg = 0.0, altKm = 0.0)
        // Satellite directly above observer
        val look = PassPredictorEngine.calculateLookAngles(
            observer = observer,
            satLatDeg = 0.0,
            satLngDeg = 0.0,
            satAltKm = 400.0
        )

        assertEquals("Elevation directly overhead should be ~90 deg", 90.0, look.elevationDeg, 0.5)
        assertEquals("Range should equal altitude", 400.0, look.rangeKm, 1.0)
    }
}
