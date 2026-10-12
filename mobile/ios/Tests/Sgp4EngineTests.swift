import XCTest
@testable import SatTrackCore

final class Sgp4EngineTests: XCTestCase {

    func testIssPropagation() {
        let iss = SatelliteEntity(
            id: 25544,
            name: "ISS (ZARYA)",
            category: "stations",
            line1: "1 25544U 98067A   24095.53472222  .00016717  00000-0  10270-3 0  9002",
            line2: "2 25544  51.6416 247.4627 0006703 130.5360 325.0288 15.49887754447413"
        )

        let state = Sgp4Engine.propagate(sat: iss)
        XCTAssertEqual(state.id, 25544)
        XCTAssertGreaterThanOrEqual(state.latDeg, -52.0)
        XCTAssertLessThanOrEqual(state.latDeg, 52.0)
        XCTAssertGreaterThan(state.altKm, 350.0)
        XCTAssertLessThan(state.altKm, 460.0)
        XCTAssertGreaterThan(state.velKmS, 7.0)
    }

    func testPassPredictorLookAngles() {
        let observer = ObserverLocation(latDeg: 37.7749, lngDeg: -122.4194, altKm: 0.03)
        // Satellite directly overhead
        let look = PassPredictorEngine.calculateLookAngles(
            observer: observer,
            satLatDeg: 37.7749,
            satLngDeg: -122.4194,
            satAltKm: 420.0
        )

        XCTAssertGreaterThan(look.elevationDeg, 85.0)
        XCTAssertLessThanOrEqual(look.elevationDeg, 90.0)
        XCTAssertEqual(look.rangeKm, 420.0, accuracy: 2.0)
    }

    func testLocalQueryParser() {
        let catalog = [
            SatelliteEntity(id: 25544, name: "ISS (ZARYA)", category: "stations", line1: "", line2: ""),
            SatelliteEntity(id: 48859, name: "GPS III-05", category: "gps", line1: "", line2: "")
        ]

        let stationRes = LocalQueryParser.parseQuery(query: "Where is the space station?", catalog: catalog)
        XCTAssertTrue(stationRes.text.contains("inhabited space stations"))
        XCTAssertEqual(stationRes.matchedSatellites.first?.id, 25544)

        let gpsRes = LocalQueryParser.parseQuery(query: "GPS navigation", catalog: catalog)
        XCTAssertTrue(gpsRes.text.contains("GNSS"))
        XCTAssertEqual(gpsRes.matchedSatellites.first?.id, 48859)
    }
}
