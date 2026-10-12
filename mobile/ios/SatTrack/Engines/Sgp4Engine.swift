import Foundation

/// High-precision, self-contained SGP4 / Keplerian Orbital Propagation Engine in Swift.
/// Converts Two-Line Element (TLE) records to WGS-84 Geodetic coordinates (Lat, Lng, Alt, Velocity).
public enum Sgp4Engine {

    public static let earthRadiusKm: Double = 6378.137
    public static let muEarth: Double = 398600.4418 // km^3 / s^2
    public static let j2: Double = 1.08262668e-3
    public static let wgs84Flattening: Double = 1.0 / 298.257223563

    public struct TleRecord {
        public let noradId: Int
        public let epochYear: Int
        public let epochDay: Double
        public let bStar: Double
        public let inclinationRad: Double
        public let raanRad: Double
        public let eccentricity: Double
        public let argPerigeeRad: Double
        public let meanAnomalyRad: Double
        public let meanMotionRadMin: Double
        public let revAtEpoch: Int
    }

    public static func parseTle(line1: String, line2: String) -> TleRecord {
        let l1 = line1.trimmingCharacters(in: .whitespacesAndNewlines)
        let l2 = line2.trimmingCharacters(in: .whitespacesAndNewlines)

        let noradId = Int(sub(l1, 2, 7)?.trimmingCharacters(in: .whitespaces) ?? "") ?? 0
        let epochYearRaw = Int(sub(l1, 18, 20)?.trimmingCharacters(in: .whitespaces) ?? "") ?? 24
        let epochYear = epochYearRaw < 57 ? 2000 + epochYearRaw : 1900 + epochYearRaw
        let epochDay = Double(sub(l1, 20, 32)?.trimmingCharacters(in: .whitespaces) ?? "") ?? 1.0

        let bStarStr = sub(l1, 53, 61)?.trimmingCharacters(in: .whitespaces).replacingOccurrences(of: " ", with: "") ?? ""
        let bStar = parseExponentialNotation(bStarStr)

        let incDeg = Double(sub(l2, 8, 16)?.trimmingCharacters(in: .whitespaces) ?? "") ?? 0.0
        let raanDeg = Double(sub(l2, 17, 25)?.trimmingCharacters(in: .whitespaces) ?? "") ?? 0.0
        let eccStr = "0." + (sub(l2, 26, 33)?.trimmingCharacters(in: .whitespaces) ?? "001")
        let ecc = Double(eccStr) ?? 0.001
        let argPerDeg = Double(sub(l2, 34, 42)?.trimmingCharacters(in: .whitespaces) ?? "") ?? 0.0
        let meanAnomDeg = Double(sub(l2, 43, 51)?.trimmingCharacters(in: .whitespaces) ?? "") ?? 0.0
        let mmRevsDay = Double(sub(l2, 52, 63)?.trimmingCharacters(in: .whitespaces) ?? "") ?? 15.0
        let revEpoch = Int(sub(l2, 63, 68)?.trimmingCharacters(in: .whitespaces) ?? "") ?? 0

        let mmRadMin = mmRevsDay * (2.0 * .pi / 1440.0)

        return TleRecord(
            noradId: noradId,
            epochYear: epochYear,
            epochDay: epochDay,
            bStar: bStar,
            inclinationRad: incDeg * .pi / 180.0,
            raanRad: raanDeg * .pi / 180.0,
            eccentricity: ecc,
            argPerigeeRad: argPerDeg * .pi / 180.0,
            meanAnomalyRad: meanAnomDeg * .pi / 180.0,
            meanMotionRadMin: mmRadMin,
            revAtEpoch: revEpoch
        )
    }

    private static func sub(_ str: String, _ start: Int, _ end: Int) -> String? {
        guard start < str.count else { return nil }
        let startIndex = str.index(str.startIndex, offsetBy: start)
        let endIndex = str.index(str.startIndex, offsetBy: min(end, str.count))
        return String(str[startIndex..<endIndex])
    }

    private static func parseExponentialNotation(_ s: String) -> Double {
        if s.isEmpty || s == "0" { return 0.0 }
        let sign: Double = s.hasPrefix("-") ? -1.0 : 1.0
        let clean = s.trimmingCharacters(in: CharacterSet(charactersIn: "+-"))
        if clean.count >= 2 {
            let mantissaStr = String(clean.prefix(clean.count - 2))
            let expStr = String(clean.suffix(2))
            if let mantissa = Double(mantissaStr), let exp = Double(expStr) {
                return sign * (mantissa * 1e-5) * pow(10.0, exp)
            }
        }
        return 0.0
    }

    /// Propagates a satellite to target timestamp (ms).
    public static func propagate(sat: SatelliteEntity, targetMs: Int64 = Int64(Date().timeIntervalSince1970 * 1000)) -> SatelliteState {
        let tle = parseTle(line1: sat.line1, line2: sat.line2)
        return propagateTle(sat: sat, tle: tle, targetMs: targetMs)
    }

    public static func propagateTle(sat: SatelliteEntity, tle: TleRecord, targetMs: Int64) -> SatelliteState {
        let jdTarget = timestampToJulianDate(targetMs)
        let jdEpoch = epochToJulianDate(year: tle.epochYear, day: tle.epochDay)
        let deltaMin = (jdTarget - jdEpoch) * 1440.0

        let nSec = tle.meanMotionRadMin / 60.0
        let a = pow(muEarth / (nSec * nSec), 1.0 / 3.0)

        let p = a * (1.0 - tle.eccentricity * tle.eccentricity)
        let cosInc = cos(tle.inclinationRad)
        let sinInc = sin(tle.inclinationRad)

        let j2Factor = 1.5 * j2 * pow(earthRadiusKm / p, 2.0) * tle.meanMotionRadMin
        let raanRate = -j2Factor * cosInc
        let argPerRate = 0.75 * j2Factor * (5.0 * cosInc * cosInc - 1.0)

        let raan = (tle.raanRad + raanRate * deltaMin).truncatingRemainder(dividingBy: 2.0 * .pi)
        let argPer = (tle.argPerigeeRad + argPerRate * deltaMin).truncatingRemainder(dividingBy: 2.0 * .pi)
        let meanAnom = (tle.meanAnomalyRad + tle.meanMotionRadMin * deltaMin).truncatingRemainder(dividingBy: 2.0 * .pi)

        // Newton-Raphson Kepler equation solve: M = E - e * sin(E)
        var eAnom = meanAnom
        for _ in 0..<16 {
            let f = eAnom - tle.eccentricity * sin(eAnom) - meanAnom
            let fPrime = 1.0 - tle.eccentricity * cos(eAnom)
            let delta = f / fPrime
            eAnom -= delta
            if abs(delta) < 1e-8 { break }
        }

        let sinNu = (sqrt(1.0 - tle.eccentricity * tle.eccentricity) * sin(eAnom)) / (1.0 - tle.eccentricity * cos(eAnom))
        let cosNu = (cos(eAnom) - tle.eccentricity) / (1.0 - tle.eccentricity * cos(eAnom))
        let nu = atan2(sinNu, cosNu)

        let r = a * (1.0 - tle.eccentricity * cos(eAnom))
        let u = (argPer + nu).truncatingRemainder(dividingBy: 2.0 * .pi)
        let xOrb = r * cos(u)
        let yOrb = r * sin(u)

        let cosRaan = cos(raan)
        let sinRaan = sin(raan)

        let xEci = xOrb * cosRaan - yOrb * cosInc * sinRaan
        let yEci = xOrb * sinRaan + yOrb * cosInc * cosRaan
        let zEci = yOrb * sinInc

        let velKmS = sqrt(muEarth * (2.0 / r - 1.0 / a))
        let velMph = velKmS * 2236.936

        let gmst = computeGmst(jdTarget)
        let cosGmst = cos(gmst)
        let sinGmst = sin(gmst)

        let xEcf = xEci * cosGmst + yEci * sinGmst
        let yEcf = -xEci * sinGmst + yEci * cosGmst
        let zEcf = zEci

        // WGS-84 Geodetic
        let lngRad = atan2(yEcf, xEcf)
        let pDist = sqrt(xEcf * xEcf + yEcf * yEcf)
        var latRad = atan2(zEcf, pDist * (1.0 - wgs84Flattening))

        for _ in 0..<6 {
            let sinLat = sin(latRad)
            let nRadius = earthRadiusKm / sqrt(1.0 - (2.0 * wgs84Flattening - wgs84Flattening * wgs84Flattening) * sinLat * sinLat)
            latRad = atan2(zEcf + (2.0 * wgs84Flattening - wgs84Flattening * wgs84Flattening) * nRadius * sinLat, pDist)
        }

        let latDeg = latRad * 180.0 / .pi
        let lngDeg = ((lngRad * 180.0 / .pi) + 180.0).truncatingRemainder(dividingBy: 360.0) - 180.0
        let altKm = r - earthRadiusKm

        let footprintAngle = acos(min(1.0, earthRadiusKm / (earthRadiusKm + max(10.0, altKm))))
        let footprintKm = earthRadiusKm * footprintAngle
        let periodMin = (2.0 * .pi * pow(a, 1.5)) / (sqrt(muEarth) * 60.0)

        return SatelliteState(
            id: sat.id,
            name: sat.name,
            latDeg: (latDeg * 100.0).rounded() / 100.0,
            lngDeg: (lngDeg * 100.0).rounded() / 100.0,
            altKm: (altKm * 10.0).rounded() / 10.0,
            velKmS: (velKmS * 100.0).rounded() / 100.0,
            velMph: (velMph * 10.0).rounded() / 10.0,
            footprintKm: footprintKm.rounded(),
            inclinationDeg: (tle.inclinationRad * 180.0 / .pi * 100.0).rounded() / 100.0,
            periodMin: (periodMin * 10.0).rounded() / 10.0,
            orbitType: sat.orbitType,
            colorHex: sat.colorHex,
            timestampMs: targetMs
        )
    }

    /// Computes full orbit ground track line segments (lat, lng pairs) over one orbital period.
    public static func computeGroundTrack(sat: SatelliteEntity, targetMs: Int64 = Int64(Date().timeIntervalSince1970 * 1000), steps: Int = 120) -> [[(lat: Double, lng: Double)]] {
        let tle = parseTle(line1: sat.line1, line2: sat.line2)
        let periodMin = max(80.0, min(1440.0, sat.periodMin))
        let periodMs = Int64(periodMin * 60.0 * 1000.0)
        let stepMs = periodMs / Int64(steps)

        var segments: [[(lat: Double, lng: Double)]] = []
        var currentSegment: [(lat: Double, lng: Double)] = []

        var prevLng: Double? = nil

        for i in 0...steps {
            let t = targetMs + Int64(i) * stepMs
            let state = propagateTle(sat: sat, tle: tle, targetMs: t)

            if let prev = prevLng, abs(state.lngDeg - prev) > 180.0 {
                if !currentSegment.isEmpty {
                    segments.append(currentSegment)
                    currentSegment = []
                }
            }

            currentSegment.append((lat: state.latDeg, lng: state.lngDeg))
            prevLng = state.lngDeg
        }

        if !currentSegment.isEmpty {
            segments.append(currentSegment)
        }

        return segments
    }

    private static func timestampToJulianDate(_ ms: Int64) -> Double {
        return (Double(ms) / 86400000.0) + 2440587.5
    }

    private static func epochToJulianDate(year: Int, day: Double) -> Double {
        var y = year - 1
        let a = y / 100
        let b = 2 - a + a / 4
        let jdJan0 = floor(365.25 * Double(y + 4716)) + floor(30.6001 * 14.0) + Double(b) - 1524.5
        return jdJan0 + day
    }

    private static func computeGmst(_ jd: Double) -> Double {
        let d = jd - 2451545.0
        var gmstDeg = 280.46061837 + 360.98564736629 * d
        gmstDeg = gmstDeg.truncatingRemainder(dividingBy: 360.0)
        if gmstDeg < 0.0 { gmstDeg += 360.0 }
        return gmstDeg * .pi / 180.0
    }
}
