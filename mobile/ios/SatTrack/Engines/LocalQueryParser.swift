import Foundation

/// First-principles Natural Language and Semantic Query Parser for iOS.
/// Resolves orbital queries offline using local catalog filters and heuristics.
public enum LocalQueryParser {

    public struct QueryResult: Equatable {
        public let text: String
        public let matchedSatellites: [SatelliteEntity]
    }

    public static func parseQuery(query: String, catalog: [SatelliteEntity]) -> QueryResult {
        let q = query.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()

        // 1. Space stations
        if q.contains("station") || q.contains("iss") || q.contains("crew") || q.contains("tiangong") {
            let sats = catalog.filter { $0.category == "stations" || $0.id == 25544 || $0.id == 48274 }
            let lines = sats.map { "• \($0.name) (NORAD \($0.id)) — Alt: \(Int($0.altitudeKm)) km, Inc: \($0.inclinationDeg)°" }.joined(separator: "\n")
            return QueryResult(
                text: "Detected \(sats.count) continuously inhabited space stations in Low Earth Orbit (LEO):\n\(lines)\n\nBoth stations operate at ~7.6 km/s (~17,100 mph) with 92-minute orbital periods.",
                matchedSatellites: sats
            )
        }

        // 2. Weather & Earth observation
        if q.contains("weather") || q.contains("climate") || q.contains("earth") || q.contains("storm") {
            let sats = catalog.filter { $0.category == "weather" || $0.category == "earth" }
            let topSats = Array(sats.prefix(4))
            let lines = topSats.map { "• \($0.name) [\($0.orbitType)] — Alt: \(Int($0.altitudeKm)) km, Inc: \($0.inclinationDeg)°" }.joined(separator: "\n")
            return QueryResult(
                text: "Identified \(sats.count) meteorological & Earth observation satellites in Sun-Synchronous and Geostationary orbits:\n\(lines)",
                matchedSatellites: topSats
            )
        }

        // 3. Navigation / GPS / GNSS
        if q.contains("gps") || q.contains("navigation") || q.contains("galileo") || q.contains("glonass") {
            let sats = catalog.filter { $0.category == "gps" }
            let topSats = Array(sats.prefix(4))
            let lines = topSats.map { "• \($0.name) (NORAD \($0.id)) — Alt: \(Int($0.altitudeKm)) km, Period: \(Int($0.periodMin)) min" }.joined(separator: "\n")
            return QueryResult(
                text: "Found \(sats.count) Global Navigation Satellite System (GNSS) spacecraft in Medium Earth Orbit:\n\(lines)\n\nThese satellites orbit twice per sidereal day at ~20,200 km altitude.",
                matchedSatellites: topSats
            )
        }

        // 4. Starlink / Constellations
        if q.contains("starlink") || q.contains("constellation") || q.contains("internet") || q.contains("iridium") {
            let sats = catalog.filter { $0.category == "starlink" }
            let topSats = Array(sats.prefix(4))
            let lines = topSats.map { "• \($0.name) — Alt: \(Int($0.altitudeKm)) km, Orbit: \($0.orbitType)" }.joined(separator: "\n")
            return QueryResult(
                text: "Found \(sats.count) broadband communication constellation satellites in 53°–86° inclination shells:\n\(lines)",
                matchedSatellites: topSats
            )
        }

        // 5. Scientific / Telescopes
        if q.contains("science") || q.contains("telescope") || q.contains("hubble") || q.contains("astronomy") {
            let sats = catalog.filter { $0.category == "science" || $0.id == 20580 }
            let lines = sats.map { "• \($0.name) — Alt: \(Int($0.altitudeKm)) km, Period: \(Int($0.periodMin)) min" }.joined(separator: "\n")
            return QueryResult(
                text: "Found \(sats.count) space astronomy and orbital observatories:\n\(lines)",
                matchedSatellites: sats
            )
        }

        // 6. Generic filter or fallback
        let matches = catalog.filter { $0.name.lowercased().contains(q) }
        if !matches.isEmpty {
            let topSats = Array(matches.prefix(5))
            let lines = topSats.map { "• \($0.name) (NORAD \($0.id)) — Orbit: \($0.orbitType)" }.joined(separator: "\n")
            return QueryResult(
                text: "Matched \(matches.count) satellites matching query '\(query)':\n\(lines)",
                matchedSatellites: topSats
            )
        }

        return QueryResult(
            text: "No direct catalog match for '\(query)'. Try searching for:\n• 'Space stations'\n• 'GPS navigation satellites'\n• 'Weather and storm trackers'\n• 'Starlink internet constellation'\n• 'Hubble Space Telescope'",
            matchedSatellites: []
        )
    }
}
