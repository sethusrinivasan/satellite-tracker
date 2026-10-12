package com.sattrack.data.repository

import com.sattrack.data.model.SatelliteEntity
import com.sattrack.data.remote.CelesTrakClient
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

class SatelliteRepository(
    private val celesTrakClient: CelesTrakClient = CelesTrakClient()
) {
    private val _satellites = MutableStateFlow<List<SatelliteEntity>>(emptyList())
    val satellites: StateFlow<List<SatelliteEntity>> = _satellites.asStateFlow()

    private val _trackedIds = MutableStateFlow<Set<Int>>(setOf(25544, 48274, 20580))
    val trackedIds: StateFlow<Set<Int>> = _trackedIds.asStateFlow()

    private val colors = listOf("#38BDF8", "#10B981", "#F59E0B", "#A855F7", "#EC4899", "#06B6D4", "#EAB308")

    init {
        loadPreseededSatellites()
    }

    private fun loadPreseededSatellites() {
        val seeds = listOf(
            // Space Stations
            SatelliteEntity(
                id = 25544,
                name = "ISS (ZARYA)",
                category = "stations",
                intlDesignator = "1998-067A",
                line1 = "1 25544U 98067A   24095.53472222  .00016717  00000-0  10270-3 0  9002",
                line2 = "2 25544  51.6416 247.4627 0006703 130.5360 325.0288 15.49887754447413",
                orbitType = "LEO",
                inclinationDeg = 51.64,
                altitudeKm = 420.0,
                periodMin = 92.9,
                isTracked = true,
                colorHex = colors[0]
            ),
            SatelliteEntity(
                id = 48274,
                name = "TIANGONG (CSS)",
                category = "stations",
                intlDesignator = "2021-035A",
                line1 = "1 48274U 21035A   24095.51234567  .00012450  00000-0  85230-4 0  9991",
                line2 = "2 48274  41.4721 180.1234 0004123 220.4501 139.5210 15.61234567167890",
                orbitType = "LEO",
                inclinationDeg = 41.47,
                altitudeKm = 388.0,
                periodMin = 92.2,
                isTracked = true,
                colorHex = colors[1]
            ),

            // Space Telescopes & Science
            SatelliteEntity(
                id = 20580,
                name = "HUBBLE SPACE TELESCOPE",
                category = "science",
                intlDesignator = "1990-037B",
                line1 = "1 20580U 90037B   24095.42109876  .00001234  00000-0  45670-4 0  9998",
                line2 = "2 20580  28.4695  75.1234 0002845 280.1234  79.8765 15.09123456865432",
                orbitType = "LEO",
                inclinationDeg = 28.47,
                altitudeKm = 535.0,
                periodMin = 95.4,
                isTracked = true,
                colorHex = colors[2]
            ),
            SatelliteEntity(
                id = 25867,
                name = "CHANDRA X-RAY OBSERVATORY",
                category = "science",
                intlDesignator = "1999-040B",
                line1 = "1 25867U 99040B   24095.12345678 -.00000123  00000-0  00000-0 0  9995",
                line2 = "2 25867  28.5123  45.6789 7854123 270.1234  89.5432  0.37891234 34567",
                orbitType = "HEO",
                inclinationDeg = 28.51,
                altitudeKm = 133000.0,
                periodMin = 3840.0,
                colorHex = colors[3]
            ),

            // Earth Observation
            SatelliteEntity(
                id = 49260,
                name = "LANDSAT 9",
                category = "earth",
                intlDesignator = "2021-088A",
                line1 = "1 49260U 21088A   24095.56789012  .00000145  00000-0  41234-4 0  9994",
                line2 = "2 49260  98.2245 170.1234 0001123  85.4321 274.6789 14.57123456134562",
                orbitType = "SSO",
                inclinationDeg = 98.22,
                altitudeKm = 705.0,
                periodMin = 98.8,
                colorHex = colors[4]
            ),
            SatelliteEntity(
                id = 40697,
                name = "SENTINEL-2A",
                category = "earth",
                intlDesignator = "2015-028A",
                line1 = "1 40697U 15028A   24095.78901234  .00000112  00000-0  31234-4 0  9998",
                line2 = "2 40697  98.5712 142.3456 0001234  65.4321 294.6789 14.30123456456781",
                orbitType = "SSO",
                inclinationDeg = 98.57,
                altitudeKm = 786.0,
                periodMin = 100.7,
                colorHex = colors[5]
            ),

            // Weather
            SatelliteEntity(
                id = 25338,
                name = "NOAA 15",
                category = "weather",
                intlDesignator = "1998-030A",
                line1 = "1 25338U 98030A   24095.34567890  .00000123  00000-0  78912-4 0  9992",
                line2 = "2 25338  98.7123 210.4567 0011234  95.1234 265.0123 14.26123456345671",
                orbitType = "SSO",
                inclinationDeg = 98.71,
                altitudeKm = 807.0,
                periodMin = 101.0,
                colorHex = colors[6]
            ),
            SatelliteEntity(
                id = 41866,
                name = "GOES 16 (EAST)",
                category = "weather",
                intlDesignator = "2016-071A",
                line1 = "1 41866U 16071A   24095.12345678  .00000012  00000-0  00000-0 0  9998",
                line2 = "2 41866   0.0212  75.2134 0001234 180.1234 179.8765  1.00271234 27123",
                orbitType = "GEO",
                inclinationDeg = 0.02,
                altitudeKm = 35786.0,
                periodMin = 1436.0,
                colorHex = colors[0]
            ),

            // GNSS Navigation
            SatelliteEntity(
                id = 48859,
                name = "GPS III-05",
                category = "gps",
                intlDesignator = "2021-054A",
                line1 = "1 48859U 21054A   24095.56789012 -.00000015  00000-0  00000-0 0  9996",
                line2 = "2 48859  55.0345 240.6789 0034567  85.1234 274.9876  2.00561234 21345",
                orbitType = "MEO",
                inclinationDeg = 55.03,
                altitudeKm = 20180.0,
                periodMin = 718.0,
                colorHex = colors[1]
            ),
            SatelliteEntity(
                id = 43564,
                name = "GALILEO 26",
                category = "gps",
                intlDesignator = "2018-060A",
                line1 = "1 43564U 18060A   24095.67890123 -.00000021  00000-0  00000-0 0  9998",
                line2 = "2 43564  56.0212 215.3456 0002345 110.1234 249.9876  1.70471234 35678",
                orbitType = "MEO",
                inclinationDeg = 56.02,
                altitudeKm = 23222.0,
                periodMin = 844.0,
                colorHex = colors[2]
            ),

            // Starlink & Constellations
            SatelliteEntity(
                id = 44238,
                name = "STARLINK-1007",
                category = "starlink",
                intlDesignator = "2019-074A",
                line1 = "1 44238U 19074A   24095.89012345  .00001567  00000-0  85432-4 0  9992",
                line2 = "2 44238  53.0512 310.1234 0001456 120.1234 239.9876 15.06123456245671",
                orbitType = "LEO",
                inclinationDeg = 53.05,
                altitudeKm = 550.0,
                periodMin = 95.6,
                colorHex = colors[3]
            ),

            // Brightest
            SatelliteEntity(
                id = 27386,
                name = "ENVISAT",
                category = "brightest",
                intlDesignator = "2002-009A",
                line1 = "1 27386U 02009A   24095.93456789  .00000123  00000-0  45678-4 0  9999",
                line2 = "2 27386  98.4212 160.4567 0001456  60.1234 299.9876 14.37123456156782",
                orbitType = "SSO",
                inclinationDeg = 98.42,
                altitudeKm = 770.0,
                periodMin = 100.2,
                colorHex = colors[4]
            )
        )

        _satellites.value = seeds
    }

    fun toggleTracking(id: Int) {
        val current = _trackedIds.value.toMutableSet()
        if (current.contains(id)) {
            current.remove(id)
        } else {
            current.add(id)
        }
        _trackedIds.value = current
    }

    fun getTrackedSatellites(): List<SatelliteEntity> {
        val set = _trackedIds.value
        return _satellites.value.filter { set.contains(it.id) }
    }

    suspend fun syncCelesTrakGroup(group: String = "stations"): Int {
        val fetched = celesTrakClient.fetchGroup(group)
        if (fetched.isNotEmpty()) {
            val map = _satellites.value.associateBy { it.id }.toMutableMap()
            fetched.forEach { map[it.id] = it }
            _satellites.value = map.values.toList()
        }
        return fetched.size
    }
}
