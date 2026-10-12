import Foundation
import Combine

/// Repository holding preseeded satellite records and active tracked state.
public final class SatelliteRepository: ObservableObject {

    public static let shared = SatelliteRepository()

    @Published public var satellites: [SatelliteEntity] = []
    @Published public var trackedIds: Set<Int> = [25544, 48274, 20580]

    private let colors = ["#38BDF8", "#10B981", "#F59E0B", "#A855F7", "#EC4899", "#06B6D4", "#EAB308"]

    public init() {
        loadPreseededSatellites()
    }

    public func toggleTracking(for id: Int) {
        if trackedIds.contains(id) {
            trackedIds.remove(id)
        } else {
            trackedIds.insert(id)
        }
        if let idx = satellites.firstIndex(where: { $0.id == id }) {
            satellites[idx].isTracked = trackedIds.contains(id)
        }
    }

    public func getById(_ id: Int) -> SatelliteEntity? {
        return satellites.first { $0.id == id }
    }

    public func loadPreseededSatellites() {
        satellites = [
            // Space Stations
            SatelliteEntity(
                id: 25544,
                name: "ISS (ZARYA)",
                category: "stations",
                intlDesignator: "1998-067A",
                line1: "1 25544U 98067A   24095.53472222  .00016717  00000-0  10270-3 0  9002",
                line2: "2 25544  51.6416 247.4627 0006703 130.5360 325.0288 15.49887754447413",
                orbitType: "LEO",
                inclinationDeg: 51.64,
                altitudeKm: 420.0,
                periodMin: 92.9,
                isTracked: true,
                colorHex: colors[0]
            ),
            SatelliteEntity(
                id: 48274,
                name: "TIANGONG (CSS)",
                category: "stations",
                intlDesignator: "2021-035A",
                line1: "1 48274U 21035A   24095.51234567  .00012450  00000-0  85230-4 0  9991",
                line2: "2 48274  41.4721 180.1234 0004123 220.4501 139.5210 15.61234567167890",
                orbitType: "LEO",
                inclinationDeg: 41.47,
                altitudeKm: 388.0,
                periodMin: 92.2,
                isTracked: true,
                colorHex: colors[1]
            ),

            // Space Telescopes & Science
            SatelliteEntity(
                id: 20580,
                name: "HUBBLE SPACE TELESCOPE",
                category: "science",
                intlDesignator: "1990-037B",
                line1: "1 20580U 90037B   24095.48712345  .00001240  00000-0  54120-4 0  9994",
                line2: "2 20580  28.4690 120.4512 0002871 280.1245  79.8451 14.98124567845120",
                orbitType: "LEO",
                inclinationDeg: 28.47,
                altitudeKm: 535.0,
                periodMin: 95.3,
                isTracked: true,
                colorHex: colors[2]
            ),

            // Earth Observation & Weather
            SatelliteEntity(
                id: 49260,
                name: "LANDSAT 9",
                category: "earth",
                intlDesignator: "2021-088A",
                line1: "1 49260U 21088A   24095.45123456  .00000450  00000-0  23410-4 0  9998",
                line2: "2 49260  98.2145  85.4512 0001240 100.1245 260.0124 14.57124567134560",
                orbitType: "SSO",
                inclinationDeg: 98.21,
                altitudeKm: 705.0,
                periodMin: 98.8,
                isTracked: false,
                colorHex: colors[3]
            ),
            SatelliteEntity(
                id: 25338,
                name: "NOAA 15",
                category: "weather",
                intlDesignator: "1998-030A",
                line1: "1 25338U 98030A   24095.40123456  .00000120  00000-0  85410-5 0  9993",
                line2: "2 25338  98.7124 110.1245 0011245  75.4512 284.7124 14.25987654345670",
                orbitType: "SSO",
                inclinationDeg: 98.71,
                altitudeKm: 807.0,
                periodMin: 101.1,
                isTracked: false,
                colorHex: colors[4]
            ),

            // Navigation & GNSS
            SatelliteEntity(
                id: 48859,
                name: "GPS III-05 (PRN 11)",
                category: "gps",
                intlDesignator: "2021-054A",
                line1: "1 48859U 21054A   24095.35123456  .00000010  00000-0  00000-0 0  9999",
                line2: "2 48859  55.1245  45.1245 0081245 190.1245 169.8451  2.00561234021450",
                orbitType: "MEO",
                inclinationDeg: 55.12,
                altitudeKm: 20200.0,
                periodMin: 718.0,
                isTracked: false,
                colorHex: colors[5]
            ),

            // Constellations
            SatelliteEntity(
                id: 44713,
                name: "STARLINK-1007",
                category: "starlink",
                intlDesignator: "2019-074A",
                line1: "1 44713U 19074A   24095.61234567  .00004512  00000-0  34120-3 0  9997",
                line2: "2 44713  53.0512 310.1245 0001542  90.4512 269.6541 15.06123456241250",
                orbitType: "LEO",
                inclinationDeg: 53.05,
                altitudeKm: 550.0,
                periodMin: 95.6,
                isTracked: false,
                colorHex: colors[6]
            )
        ]
    }
}
