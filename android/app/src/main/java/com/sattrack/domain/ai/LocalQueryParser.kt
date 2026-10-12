package com.sattrack.domain.ai

import com.sattrack.data.model.SatelliteEntity

/**
 * First-principles Natural Language and Semantic Query Parser.
 * Resolves natural language orbital queries offline using local catalog filters and heuristics.
 */
object LocalQueryParser {

    data class QueryResult(
        val text: String,
        val matchedSatellites: List<SatelliteEntity>
    )

    fun parseQuery(query: String, catalog: List<SatelliteEntity>): QueryResult {
        val q = query.trim().lowercase()

        // 1. Space stations
        if (q.contains("station") || q.contains("iss") || q.contains("crew") || q.contains("tiangong")) {
            val sats = catalog.filter { it.category == "stations" || it.id == 25544 || it.id == 48274 }
            return QueryResult(
                text = "Detected ${sats.size} continuously inhabited space stations in Low Earth Orbit (LEO):\n" +
                        sats.joinToString("\n") { "• ${it.name} (NORAD ${it.id}) — Alt: ${it.altitudeKm.toInt()} km, Inc: ${it.inclinationDeg}°" } +
                        "\n\nBoth stations operate at ~7.6 km/s (~17,100 mph) with 92-minute orbital periods.",
                matchedSatellites = sats
            )
        }

        // 2. Weather & Earth observation
        if (q.contains("weather") || q.contains("climate") || q.contains("earth") || q.contains("storm")) {
            val sats = catalog.filter { it.category == "weather" || it.category == "earth" }
            return QueryResult(
                text = "Identified ${sats.size} meteorological & Earth observation satellites in Sun-Synchronous and Geostationary orbits:\n" +
                        sats.take(4).joinToString("\n") { "• ${it.name} [${it.orbitType}] — Alt: ${it.altitudeKm.toInt()} km, Inc: ${it.inclinationDeg}°" },
                matchedSatellites = sats.take(4)
            )
        }

        // 3. Navigation / GPS / GNSS
        if (q.contains("gps") || q.contains("navigation") || q.contains("galileo") || q.contains("glonass")) {
            val sats = catalog.filter { it.category == "gps" }
            return QueryResult(
                text = "Found ${sats.size} Global Navigation Satellite System (GNSS) spacecraft in Medium Earth Orbit:\n" +
                        sats.take(4).joinToString("\n") { "• ${it.name} (NORAD ${it.id}) — Alt: ${it.altitudeKm.toInt()} km, Period: ${it.periodMin.toInt()} min" } +
                        "\n\nThese satellites orbit twice per sidereal day at ~20,200 km altitude.",
                matchedSatellites = sats.take(4)
            )
        }

        // 4. Starlink / Constellations
        if (q.contains("starlink") || q.contains("constellation") || q.contains("internet") || q.contains("iridium")) {
            val sats = catalog.filter { it.category == "starlink" }
            return QueryResult(
                text = "Found ${sats.size} broadband communication constellation satellites in 53°–86° inclination shells:\n" +
                        sats.take(4).joinToString("\n") { "• ${it.name} — Alt: ${it.altitudeKm.toInt()} km, Orbit: ${it.orbitType}" },
                matchedSatellites = sats.take(4)
            )
        }

        // 5. High altitude / GEO / MEO
        if (q.contains("high") || q.contains("geo") || q.contains("meo") || q.contains("altitude >") || q.contains("highest")) {
            val sats = catalog.filter { it.altitudeKm > 10000.0 }.sortedByDescending { it.altitudeKm }
            return QueryResult(
                text = "Found ${sats.size} high-altitude spacecraft operating above 10,000 km:\n" +
                        sats.take(4).joinToString("\n") { "• ${it.name} — Alt: ${it.altitudeKm.toInt()} km (${it.orbitType})" },
                matchedSatellites = sats.take(4)
            )
        }

        // 6. Astronomy / Telescopes
        if (q.contains("telescope") || q.contains("science") || q.contains("hubble") || q.contains("chandra") || q.contains("space")) {
            val sats = catalog.filter { it.category == "science" }
            return QueryResult(
                text = "Found ${sats.size} scientific observatories and space telescopes in orbit:\n" +
                        sats.take(4).joinToString("\n") { "• ${it.name} — Alt: ${it.altitudeKm.toInt()} km, Inc: ${it.inclinationDeg}°" },
                matchedSatellites = sats.take(4)
            )
        }

        // 7. General search fallback
        val matching = catalog.filter {
            it.name.lowercase().contains(q) ||
                    it.id.toString().contains(q) ||
                    it.category.lowercase().contains(q)
        }

        if (matching.isNotEmpty()) {
            return QueryResult(
                text = "Found ${matching.size} matching satellites for \"$query\":\n" +
                        matching.take(4).joinToString("\n") { "• ${it.name} (NORAD ${it.id}) — ${it.orbitType} (${it.altitudeKm.toInt()} km)" },
                matchedSatellites = matching.take(4)
            )
        }

        return QueryResult(
            text = "The on-device SGP4 propagation engine is actively tracking spacecraft. You can select satellites from the Catalog, inspect ground tracks on the 2D/3D map, or configure an optional remote AI provider in Settings.",
            matchedSatellites = catalog.take(2)
        )
    }
}
