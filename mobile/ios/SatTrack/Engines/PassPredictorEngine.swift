import Foundation

/// Topocentric Overpass Predictor Engine for iOS in Swift.
/// Calculates exact Acquisition of Signal (AOS), Peak Culmination Elevation,
/// Loss of Signal (LOS), and Azimuth trajectories for an observer ground station.
public enum PassPredictorEngine {

    public struct LookAngles {
        public let azimuthDeg: Double
        public let elevationDeg: Double
        public let rangeKm: Double
    }

    public static func calculateLookAngles(
        observer: ObserverLocation,
        satLatDeg: Double,
        satLngDeg: Double,
        satAltKm: Double
    ) -> LookAngles {
        let obsLatRad = observer.latDeg * .pi / 180.0
        let obsLngRad = observer.lngDeg * .pi / 180.0
        let obsR = Sgp4Engine.earthRadiusKm + observer.altKm

        let obsX = obsR * cos(obsLatRad) * cos(obsLngRad)
        let obsY = obsR * cos(obsLatRad) * sin(obsLngRad)
        let obsZ = obsR * sin(obsLatRad)

        let satLatRad = satLatDeg * .pi / 180.0
        let satLngRad = satLngDeg * .pi / 180.0
        let satR = Sgp4Engine.earthRadiusKm + satAltKm

        let satX = satR * cos(satLatRad) * cos(satLngRad)
        let satY = satR * cos(satLatRad) * sin(satLngRad)
        let satZ = satR * sin(satLatRad)

        let dx = satX - obsX
        let dy = satY - obsY
        let dz = satZ - obsZ
        let range = sqrt(dx * dx + dy * dy + dz * dz)

        // Transform to Topocentric frame (North, East, Up)
        let sinLat = sin(obsLatRad)
        let cosLat = cos(obsLatRad)
        let sinLng = sin(obsLngRad)
        let cosLng = cos(obsLngRad)

        let north = -sinLat * cosLng * dx - sinLat * sinLng * dy + cosLat * dz
        let east = -sinLng * dx + cosLng * dy
        let up = cosLat * cosLng * dx + cosLat * sinLng * dy + sinLat * dz

        let elevationRad = asin(max(-1.0, min(1.0, up / range)))
        var azimuthRad = atan2(east, north)
        if azimuthRad < 0.0 { azimuthRad += 2.0 * .pi }

        return LookAngles(
            azimuthDeg: azimuthRad * 180.0 / .pi,
            elevationDeg: elevationRad * 180.0 / .pi,
            rangeKm: range
        )
    }

    /// Scans the upcoming 24 hours at 30-second steps for overpasses above minElevationDeg.
    public static func predictPasses(
        sat: SatelliteEntity,
        observer: ObserverLocation,
        minElevationDeg: Double = 10.0,
        maxPasses: Int = 8
    ) -> [PassPrediction] {
        let tle = Sgp4Engine.parseTle(line1: sat.line1, line2: sat.line2)
        let nowMs = Int64(Date().timeIntervalSince1970 * 1000)
        let horizonMs: Int64 = 86400000 // 24 hours
        let stepMs: Int64 = 30000 // 30 seconds

        var passes: [PassPrediction] = []
        var inPass = false
        var aosTime: Int64 = 0
        var aosAzimuth: Double = 0.0
        var maxElev: Double = -90.0
        var maxElevTime: Int64 = 0
        var maxAzimuth: Double = 0.0

        var t = nowMs
        let endT = nowMs + horizonMs

        while t < endT {
            let state = Sgp4Engine.propagateTle(sat: sat, tle: tle, targetMs: t)
            let look = calculateLookAngles(observer: observer, satLatDeg: state.latDeg, satLngDeg: state.lngDeg, satAltKm: state.altKm)

            if look.elevationDeg >= minElevationDeg {
                if !inPass {
                    inPass = true
                    aosTime = t
                    aosAzimuth = look.azimuthDeg
                    maxElev = look.elevationDeg
                    maxElevTime = t
                    maxAzimuth = look.azimuthDeg
                } else {
                    if look.elevationDeg > maxElev {
                        maxElev = look.elevationDeg
                        maxElevTime = t
                        maxAzimuth = look.azimuthDeg
                    }
                }
            } else if inPass {
                inPass = false
                let losTime = t
                let losAzimuth = look.azimuthDeg
                let durationSec = (losTime - aosTime) / 1000

                let quality: String
                if maxElev >= 60.0 {
                    quality = "EXCELLENT"
                } else if maxElev >= 30.0 {
                    quality = "GOOD"
                } else {
                    quality = "FAIR"
                }

                passes.append(PassPrediction(
                    satId: sat.id,
                    satName: sat.name,
                    aosTimeMs: aosTime,
                    aosAzimuthDeg: (aosAzimuth * 10.0).rounded() / 10.0,
                    maxElevDeg: (maxElev * 10.0).rounded() / 10.0,
                    maxElevTimeMs: maxElevTime,
                    maxAzimuthDeg: (maxAzimuth * 10.0).rounded() / 10.0,
                    losTimeMs: losTime,
                    losAzimuthDeg: (losAzimuth * 10.0).rounded() / 10.0,
                    durationSec: durationSec,
                    quality: quality
                ))

                if passes.count >= maxPasses { break }
            }

            t += stepMs
        }

        return passes
    }

    public static func azimuthToCompassDirection(_ degrees: Double) -> String {
        let directions = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
        let index = Int(((degrees.truncatingRemainder(dividingBy: 360.0) + 360.0).truncatingRemainder(dividingBy: 360.0) / 22.5) + 0.5) % 16
        return directions[index]
    }
}
