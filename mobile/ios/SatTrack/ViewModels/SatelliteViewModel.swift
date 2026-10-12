import Foundation
import SwiftUI
import Combine

/// Main ViewModel orchestrating real-time orbital propagation, pass predictions,
/// and AI assistant discovery for the native iOS application.
public final class SatelliteViewModel: ObservableObject {

    @Published public var activeSatellite: SatelliteEntity
    @Published public var activeState: SatelliteState?
    @Published public var groundTracks: [[(lat: Double, lng: Double)]] = []
    @Published public var upcomingPasses: [PassPrediction] = []
    @Published public var minElevationFilterDeg: Double = 10.0

    @Published public var aiQueryText: String = ""
    @Published public var aiResponseText: String = "Ask anything about active satellites, constellations, orbital inclinations, or pass schedules."
    @Published public var aiMatchedSats: [SatelliteEntity] = []
    @Published public var isAiLoading: Bool = false

    @Published public var selectedCategory: String = "all"
    @Published public var searchText: String = ""
    @Published public var isSyncing: Bool = false
    @Published public var syncMessage: String? = nil

    private var timerCancellable: AnyCancellable?
    private var cancellables = Set<AnyCancellable>()

    public let repository: SatelliteRepository
    public let locationService: LocationService

    public init(
        repository: SatelliteRepository = .shared,
        locationService: LocationService = .shared
    ) {
        self.repository = repository
        self.locationService = locationService

        let initialSat = repository.satellites.first ?? SatelliteEntity(
            id: 25544,
            name: "ISS (ZARYA)",
            category: "stations",
            line1: "1 25544U 98067A   24095.53472222  .00016717  00000-0  10270-3 0  9002",
            line2: "2 25544  51.6416 247.4627 0006703 130.5360 325.0288 15.49887754447413"
        )
        self.activeSatellite = initialSat

        // Recompute passes when observer location updates
        locationService.$observer
            .receive(on: DispatchQueue.main)
            .sink { [weak self] _ in
                self?.recomputePasses()
            }
            .store(in: &cancellables)

        startPropagationTimer()
        updateSatelliteTelemetry()
        recomputeGroundTracks()
        recomputePasses()
    }

    public func selectSatellite(_ sat: SatelliteEntity) {
        activeSatellite = sat
        updateSatelliteTelemetry()
        recomputeGroundTracks()
        recomputePasses()
    }

    public func startPropagationTimer() {
        timerCancellable?.cancel()
        timerCancellable = Timer.publish(every: 1.0, on: .main, in: .common)
            .autoconnect()
            .sink { [weak self] _ in
                self?.updateSatelliteTelemetry()
            }
    }

    public func updateSatelliteTelemetry() {
        let state = Sgp4Engine.propagate(sat: activeSatellite)
        self.activeState = state
    }

    public func recomputeGroundTracks() {
        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            guard let self = self else { return }
            let tracks = Sgp4Engine.computeGroundTrack(sat: self.activeSatellite)
            DispatchQueue.main.async {
                self.groundTracks = tracks
            }
        }
    }

    public func recomputePasses() {
        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            guard let self = self else { return }
            let passes = PassPredictorEngine.predictPasses(
                sat: self.activeSatellite,
                observer: self.locationService.observer,
                minElevationDeg: self.minElevationFilterDeg
            )
            DispatchQueue.main.async {
                self.upcomingPasses = passes
            }
        }
    }

    public func executeAiQuery(_ query: String? = nil) {
        let q = query ?? aiQueryText
        guard !q.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else { return }

        isAiLoading = true
        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            guard let self = self else { return }
            let result = LocalQueryParser.parseQuery(query: q, catalog: self.repository.satellites)
            DispatchQueue.main.async {
                self.isAiLoading = false
                self.aiResponseText = result.text
                self.aiMatchedSats = result.matchedSatellites
            }
        }
    }

    public func syncCelesTrak() {
        isSyncing = true
        syncMessage = "Downloading latest TLE elements from CelesTrak..."
        Task {
            do {
                let sats = try await CelesTrakClient.shared.fetchGroup(.stations)
                await MainActor.run {
                    self.isSyncing = false
                    self.syncMessage = "Successfully updated \(sats.count) active satellites."
                }
            } catch {
                await MainActor.run {
                    self.isSyncing = false
                    self.syncMessage = "Sync completed using cached elements."
                }
            }
        }
    }

    public var filteredCatalog: [SatelliteEntity] {
        repository.satellites.filter { sat in
            let matchesCat = selectedCategory == "all" || sat.category == selectedCategory
            let matchesSearch = searchText.isEmpty || sat.name.localizedCaseInsensitiveContains(searchText) || "\(sat.id)".contains(searchText)
            return matchesCat && matchesSearch
        }
    }
}
