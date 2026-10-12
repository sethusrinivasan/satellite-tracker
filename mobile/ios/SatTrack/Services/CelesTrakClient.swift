import Foundation

/// Network client for fetching active Two-Line Element (TLE) records from CelesTrak.
public final class CelesTrakClient {

    public static let shared = CelesTrakClient()

    private let session: URLSession

    public init(session: URLSession = .shared) {
        self.session = session
    }

    public enum CelesTrakGroup: String, CaseIterable {
        case active = "active"
        case stations = "stations"
        case visual = "visual"
        case starlink = "starlink"
        case weather = "weather"
        case gnss = "gnss"

        public var displayName: String {
            switch self {
            case .active: return "All Active"
            case .stations: return "Space Stations"
            case .visual: return "Brightest (Visual)"
            case .starlink: return "Starlink Constellation"
            case .weather: return "Weather & Earth"
            case .gnss: return "GPS & Navigation"
            }
        }
    }

    /// Fetches TLE records for a specified group from CelesTrak GP API.
    public func fetchGroup(_ group: CelesTrakGroup = .stations) async throws -> [SatelliteEntity] {
        guard let url = URL(string: "https://celestrak.org/NORAD/elements/gp.php?GROUP=\(group.rawValue)&FORMAT=tle") else {
            throw URLError(.badURL)
        }

        var request = URLRequest(url: url)
        request.timeoutInterval = 30
        request.setValue("SatTrack-iOS/1.0", forHTTPHeaderField: "User-Agent")

        let (data, response) = try await session.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse, (200...299).contains(httpResponse.statusCode) else {
            throw URLError(.badServerResponse)
        }

        guard let rawText = String(data: data, encoding: .utf8) else {
            throw URLError(.cannotDecodeContentData)
        }

        return parseTleStream(rawText, defaultCategory: group.rawValue)
    }

    /// Parses raw TLE text stream (name, line 1, line 2) into SatelliteEntities.
    public func parseTleStream(_ raw: String, defaultCategory: String = "general") -> [SatelliteEntity] {
        let lines = raw.components(separatedBy: .newlines).map { $0.trimmingCharacters(in: .whitespaces) }.filter { !$0.isEmpty }
        var result: [SatelliteEntity] = []

        var i = 0
        while i + 2 < lines.count {
            let name = lines[i]
            let l1 = lines[i + 1]
            let l2 = lines[i + 2]

            if l1.hasPrefix("1 ") && l2.hasPrefix("2 ") {
                let noradId = Int(l1.prefix(7).suffix(5).trimmingCharacters(in: .whitespaces)) ?? result.count + 1
                let inc = Double(l2.prefix(16).suffix(8).trimmingCharacters(in: .whitespaces)) ?? 0.0

                result.append(SatelliteEntity(
                    id: noradId,
                    name: name,
                    category: defaultCategory,
                    line1: l1,
                    line2: l2,
                    inclinationDeg: inc,
                    isTracked: false
                ))
                i += 3
            } else {
                i += 1
            }
        }

        return result
    }
}
