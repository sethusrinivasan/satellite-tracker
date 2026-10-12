package com.sattrack

import com.sattrack.data.model.SatelliteEntity
import com.sattrack.domain.ai.LocalQueryParser
import org.junit.Assert.*
import org.junit.Test

class LocalQueryParserTest {

    private val sampleCatalog = listOf(
        SatelliteEntity(
            id = 25544,
            name = "ISS (ZARYA)",
            category = "stations",
            line1 = "1 25544U 98067A   24095.53472222  .00016717  00000-0  10270-3 0  9002",
            line2 = "2 25544  51.6416 247.4627 0006703 130.5360 325.0288 15.49887754447413"
        ),
        SatelliteEntity(
            id = 48859,
            name = "GPS III-05",
            category = "gps",
            line1 = "1 48859U 21054A   24095.56789012 -.00000015  00000-0  00000-0 0  9996",
            line2 = "2 48859  55.0345 240.6789 0034567  85.1234 274.9876  2.00561234 21345",
            altitudeKm = 20180.0
        ),
        SatelliteEntity(
            id = 25338,
            name = "NOAA 15",
            category = "weather",
            line1 = "1 25338U 98030A   24095.34567890  .00000123  00000-0  78912-4 0  9992",
            line2 = "2 25338  98.7123 210.4567 0011234  95.1234 265.0123 14.26123456345671",
            altitudeKm = 807.0
        )
    )

    @Test
    fun testParseStationsQuery() {
        val res = LocalQueryParser.parseQuery("Show me the space station", sampleCatalog)
        assertTrue(res.text.contains("ISS"))
        assertEquals(1, res.matchedSatellites.size)
        assertEquals(25544, res.matchedSatellites[0].id)
    }

    @Test
    fun testParseGpsQuery() {
        val res = LocalQueryParser.parseQuery("Find GPS satellites", sampleCatalog)
        assertTrue(res.text.contains("GNSS"))
        assertEquals(1, res.matchedSatellites.size)
        assertEquals(48859, res.matchedSatellites[0].id)
    }

    @Test
    fun testParseWeatherQuery() {
        val res = LocalQueryParser.parseQuery("Which weather satellites are active?", sampleCatalog)
        assertTrue(res.text.contains("meteorological"))
        assertEquals(1, res.matchedSatellites.size)
        assertEquals(25338, res.matchedSatellites[0].id)
    }
}
