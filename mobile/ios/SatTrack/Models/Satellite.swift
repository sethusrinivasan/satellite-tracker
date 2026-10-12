import Foundation

/// Core satellite data model representing a parsed TLE entity.
public struct SatelliteEntity: Identifiable, Codable, Equatable, Hashable {
    public let id: Int // NORAD Catalog ID
    public let name: String
    public let category: String
    public let intlDesignator: String
    public let line1: String
    public let line2: String
    public let orbitType: String
    public let inclinationDeg: Double
    public let altitudeKm: Double
    public let periodMin: Double
    public var isTracked: Bool
    public let colorHex: String

    public init(
        id: Int,
        name: String,
        category: String,
        intlDesignator: String = "",
        line1: String,
        line2: String,
        orbitType: String = "LEO",
        inclinationDeg: Double = 0.0,
        altitudeKm: Double = 400.0,
        periodMin: Double = 90.0,
        isTracked: Bool = false,
        colorHex: String = "#38BDF8"
    ) {
        self.id = id
        self.name = name
        self.category = category
        self.intlDesignator = intlDesignator
        self.line1 = line1
        self.line2 = line2
        self.orbitType = orbitType
        self.inclinationDeg = inclinationDeg
        self.altitudeKm = altitudeKm
        self.periodMin = periodMin
        self.isTracked = isTracked
        self.colorHex = colorHex
    }
}

/// Instantaneous sub-satellite point and orbital telemetry state.
public struct SatelliteState: Identifiable, Equatable {
    public let id: Int
    public let name: String
    public let latDeg: Double
    public let lngDeg: Double
    public let altKm: Double
    public let velKmS: Double
    public let velMph: Double
    public let footprintKm: Double
    public let inclinationDeg: Double
    public let periodMin: Double
    public let orbitType: String
    public let colorHex: String
    public let timestampMs: Int64

    public init(
        id: Int,
        name: String,
        latDeg: Double,
        lngDeg: Double,
        altKm: Double,
        velKmS: Double,
        velMph: Double,
        footprintKm: Double,
        inclinationDeg: Double,
        periodMin: Double,
        orbitType: String,
        colorHex: String,
        timestampMs: Int64 = Int64(Date().timeIntervalSince1970 * 1000)
    ) {
        self.id = id
        self.name = name
        self.latDeg = latDeg
        self.lngDeg = lngDeg
        self.altKm = altKm
        self.velKmS = velKmS
        self.velMph = velMph
        self.footprintKm = footprintKm
        self.inclinationDeg = inclinationDeg
        self.periodMin = periodMin
        self.orbitType = orbitType
        self.colorHex = colorHex
        self.timestampMs = timestampMs
    }
}

/// Ground station observer coordinates for pass calculations.
public struct ObserverLocation: Equatable {
    public var latDeg: Double
    public var lngDeg: Double
    public var altKm: Double
    public var name: String

    public init(
        latDeg: Double = 37.7749,
        lngDeg: Double = -122.4194,
        altKm: Double = 0.03,
        name: String = "Observer (San Francisco)"
    ) {
        self.latDeg = latDeg
        self.lngDeg = lngDeg
        self.altKm = altKm
        self.name = name
    }
}

/// Pass prediction for an upcoming visible satellite pass.
public struct PassPrediction: Identifiable, Equatable {
    public var id: String { "\(satId)-\(aosTimeMs)" }
    public let satId: Int
    public let satName: String
    public let aosTimeMs: Int64
    public let aosAzimuthDeg: Double
    public let maxElevDeg: Double
    public let maxElevTimeMs: Int64
    public let maxAzimuthDeg: Double
    public let losTimeMs: Int64
    public let losAzimuthDeg: Double
    public let durationSec: Int64
    public let quality: String // EXCELLENT, GOOD, FAIR

    public init(
        satId: Int,
        satName: String,
        aosTimeMs: Int64,
        aosAzimuthDeg: Double,
        maxElevDeg: Double,
        maxElevTimeMs: Int64,
        maxAzimuthDeg: Double,
        losTimeMs: Int64,
        losAzimuthDeg: Double,
        durationSec: Int64,
        quality: String
    ) {
        self.satId = satId
        self.satName = satName
        self.aosTimeMs = aosTimeMs
        self.aosAzimuthDeg = aosAzimuthDeg
        self.maxElevDeg = maxElevDeg
        self.maxElevTimeMs = maxElevTimeMs
        self.maxAzimuthDeg = maxAzimuthDeg
        self.losTimeMs = losTimeMs
        self.losAzimuthDeg = losAzimuthDeg
        self.durationSec = durationSec
        self.quality = quality
    }
}
