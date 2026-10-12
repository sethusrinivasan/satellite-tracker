import SwiftUI

/// Satellite Catalog View with category filtering, search, and tracking toggles.
public struct CatalogView: View {
    @EnvironmentObject var viewModel: SatelliteViewModel

    private let categories = [
        ("all", "All"),
        ("stations", "Space Stations"),
        ("weather", "Weather"),
        ("science", "Science"),
        ("gps", "GPS / GNSS"),
        ("starlink", "Starlink")
    ]

    public init() {}

    public var body: some View {
        NavigationView {
            VStack(spacing: 0) {
                // Search Bar
                HStack {
                    Image(systemName: "magnifyingglass")
                        .foregroundColor(.gray)
                    TextField("Search satellite name or NORAD ID...", text: $viewModel.searchText)
                        .foregroundColor(.white)
                    if !viewModel.searchText.isEmpty {
                        Button(action: { viewModel.searchText = "" }) {
                            Image(systemName: "xmark.circle.fill")
                                .foregroundColor(.gray)
                        }
                    }
                }
                .padding(10)
                .background(Color(white: 0.12))
                .cornerRadius(10)
                .padding(.horizontal)
                .padding(.vertical, 8)

                // Category Chips Scroll
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 8) {
                        ForEach(categories, id: \.0) { catId, catName in
                            Button(action: { viewModel.selectedCategory = catId }) {
                                Text(catName)
                                    .font(.system(size: 13, weight: .semibold))
                                    .padding(.horizontal, 14)
                                    .padding(.vertical, 7)
                                    .background(viewModel.selectedCategory == catId ? Color(hex: "#38BDF8") : Color(white: 0.12))
                                    .foregroundColor(viewModel.selectedCategory == catId ? .black : .white)
                                    .cornerRadius(20)
                            }
                        }
                    }
                    .padding(.horizontal)
                    .padding(.bottom, 8)
                }

                // Satellite List
                List {
                    ForEach(viewModel.filteredCatalog) { sat in
                        SatelliteRowView(
                            sat: sat,
                            isSelected: sat.id == viewModel.activeSatellite.id,
                            isTracked: viewModel.repository.trackedIds.contains(sat.id),
                            onSelect: { viewModel.selectSatellite(sat) },
                            onToggleTrack: { viewModel.repository.toggleTracking(for: sat.id) }
                        )
                        .listRowBackground(Color.black)
                    }
                }
                .listStyle(.plain)
            }
            .navigationTitle("Satellite Catalog")
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button(action: { viewModel.syncCelesTrak() }) {
                        if viewModel.isSyncing {
                            ProgressView().scaleEffect(0.8)
                        } else {
                            Image(systemName: "arrow.clockwise")
                        }
                    }
                }
            }
            .background(Color.black.edgesIgnoringSafeArea(.all))
        }
    }
}

private struct SatelliteRowView: View {
    let sat: SatelliteEntity
    let isSelected: Bool
    let isTracked: Bool
    let onSelect: () -> Void
    let onToggleTrack: () -> Void

    var body: some View {
        HStack {
            Button(action: onSelect) {
                HStack(spacing: 12) {
                    Circle()
                        .fill(Color(hex: sat.colorHex))
                        .frame(width: 10, height: 10)

                    VStack(alignment: .leading, spacing: 3) {
                        HStack {
                            Text(sat.name)
                                .font(.system(size: 15, weight: .bold))
                                .foregroundColor(.white)
                            if isSelected {
                                Text("ACTIVE")
                                    .font(.system(size: 9, weight: .bold))
                                    .padding(.horizontal, 6)
                                    .padding(.vertical, 2)
                                    .background(Color.green.opacity(0.2))
                                    .foregroundColor(.green)
                                    .cornerRadius(4)
                            }
                        }

                        Text("NORAD \(sat.id) • \(sat.orbitType) • Inc \(sat.inclinationDeg, specifier: "%.1f")° • Alt \(Int(sat.altitudeKm)) km")
                            .font(.system(size: 11))
                            .foregroundColor(.gray)
                    }
                }
            }
            .buttonStyle(.plain)

            Spacer()

            Button(action: onToggleTrack) {
                Image(systemName: isTracked ? "pin.fill" : "pin")
                    .foregroundColor(isTracked ? Color(hex: "#38BDF8") : .gray)
                    .padding(8)
            }
            .buttonStyle(.plain)
        }
        .padding(.vertical, 6)
    }
}
