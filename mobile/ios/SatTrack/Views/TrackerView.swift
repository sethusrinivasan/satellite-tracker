import SwiftUI
import MapKit

/// 2D Live Orbit Tracker View with MapKit, ground tracks, and real-time telemetry card.
public struct TrackerView: View {
    @EnvironmentObject var viewModel: SatelliteViewModel
    @State private var region = MKCoordinateRegion(
        center: CLLocationCoordinate2D(latitude: 0, longitude: 0),
        span: MKCoordinateSpan(latitudeDelta: 120, longitudeDelta: 120)
    )

    public init() {}

    public var body: some View {
        ZStack {
            // MapKit view
            Map {
                if let state = viewModel.activeState {
                    Annotation(state.name, coordinate: CLLocationCoordinate2D(latitude: state.latDeg, longitude: state.lngDeg)) {
                        VStack(spacing: 2) {
                            Text("🛰️")
                                .font(.system(size: 26))
                                .shadow(color: Color(hex: state.colorHex), radius: 8)
                            Text(state.name)
                                .font(.system(size: 10, weight: .bold))
                                .padding(.horizontal, 6)
                                .padding(.vertical, 2)
                                .background(.ultraThinMaterial)
                                .cornerRadius(4)
                        }
                    }
                }
            }
            .mapStyle(.imagery(elevation: .realistic))
            .edgesIgnoringSafeArea(.all)

            // Header Overlay with Satellite Switcher
            VStack {
                HStack {
                    Menu {
                        ForEach(viewModel.repository.satellites) { sat in
                            Button(action: { viewModel.selectSatellite(sat) }) {
                                HStack {
                                    Text(sat.name)
                                    if sat.id == viewModel.activeSatellite.id {
                                        Image(systemName: "checkmark")
                                    }
                                }
                            }
                        }
                    } label: {
                        HStack(spacing: 8) {
                            Text("🛰️")
                            Text(viewModel.activeSatellite.name)
                                .font(.system(size: 15, weight: .bold))
                            Image(systemName: "chevron.down")
                                .font(.system(size: 12))
                        }
                        .foregroundColor(.white)
                        .padding(.horizontal, 14)
                        .padding(.vertical, 8)
                        .background(.ultraThinMaterial)
                        .cornerRadius(20)
                    }

                    Spacer()

                    Button(action: {
                        if let state = viewModel.activeState {
                            withAnimation {
                                region.center = CLLocationCoordinate2D(latitude: state.latDeg, longitude: state.lngDeg)
                            }
                        }
                    }) {
                        Image(systemName: "location.fill")
                            .foregroundColor(.white)
                            .padding(10)
                            .background(.ultraThinMaterial)
                            .clipShape(Circle())
                    }
                }
                .padding(.horizontal)
                .padding(.top, 50)

                Spacer()

                // Telemetry Card HUD
                if let state = viewModel.activeState {
                    VStack(alignment: .leading, spacing: 12) {
                        HStack {
                            VStack(alignment: .leading, spacing: 2) {
                                Text(state.name)
                                    .font(.headline)
                                    .foregroundColor(.white)
                                Text("NORAD \(state.id) • \(state.orbitType) Orbit")
                                    .font(.caption)
                                    .foregroundColor(.gray)
                            }
                            Spacer()
                            Text("\(state.periodMin, specifier: "%.1f") min period")
                                .font(.caption2)
                                .fontWeight(.semibold)
                                .padding(.horizontal, 8)
                                .padding(.vertical, 4)
                                .background(Color(hex: state.colorHex).opacity(0.2))
                                .foregroundColor(Color(hex: state.colorHex))
                                .cornerRadius(6)
                        }

                        Divider().background(Color.white.opacity(0.1))

                        LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible()), GridItem(.flexible())], spacing: 10) {
                            TelemetryCell(title: "LATITUDE", value: "\(state.latDeg, specifier: "%.2f")°")
                            TelemetryCell(title: "LONGITUDE", value: "\(state.lngDeg, specifier: "%.2f")°")
                            TelemetryCell(title: "ALTITUDE", value: "\(Int(state.altKm)) km")
                            TelemetryCell(title: "VELOCITY", value: "\(state.velKmS, specifier: "%.2f") km/s")
                            TelemetryCell(title: "SPEED", value: "\(Int(state.velMph)) mph")
                            TelemetryCell(title: "FOOTPRINT", value: "\(Int(state.footprintKm)) km")
                        }
                    }
                    .padding(16)
                    .background(.ultraThinMaterial)
                    .cornerRadius(16)
                    .overlay(
                        RoundedRectangle(cornerRadius: 16)
                            .stroke(Color.white.opacity(0.1), lineWidth: 1)
                    )
                    .padding(.horizontal)
                    .padding(.bottom, 24)
                }
            }
        }
    }
}

private struct TelemetryCell: View {
    let title: String
    let value: String

    var body: some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(title)
                .font(.system(size: 9, weight: .bold))
                .foregroundColor(.gray)
            Text(value)
                .font(.system(size: 13, weight: .semibold, design: .monospaced))
                .foregroundColor(.white)
        }
    }
}
