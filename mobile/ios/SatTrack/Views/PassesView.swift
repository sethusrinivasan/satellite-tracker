import SwiftUI

/// Observer Passes View displaying upcoming visible satellite passes and look-angles.
public struct PassesView: View {
    @EnvironmentObject var viewModel: SatelliteViewModel

    public init() {}

    public var body: some View {
        NavigationView {
            ScrollView {
                VStack(spacing: 16) {
                    // Observer Location Card
                    VStack(alignment: .leading, spacing: 10) {
                        HStack {
                            VStack(alignment: .leading, spacing: 2) {
                                Text("OBSERVER GROUND STATION")
                                    .font(.system(size: 10, weight: .bold))
                                    .foregroundColor(.gray)
                                Text(viewModel.locationService.observer.name)
                                    .font(.system(size: 14, weight: .semibold))
                                    .foregroundColor(.white)
                                Text("\(viewModel.locationService.observer.latDeg, specifier: "%.3f")° N, \(viewModel.locationService.observer.lngDeg, specifier: "%.3f")° E")
                                    .font(.system(size: 12, design: .monospaced))
                                    .foregroundColor(.gray)
                            }

                            Spacer()

                            Button(action: {
                                viewModel.locationService.requestLocation()
                            }) {
                                HStack(spacing: 4) {
                                    if viewModel.locationService.isLocating {
                                        ProgressView().scaleEffect(0.7)
                                    } else {
                                        Image(systemName: "location.fill")
                                    }
                                    Text("GPS")
                                        .font(.system(size: 13, weight: .bold))
                                }
                                .padding(.horizontal, 12)
                                .padding(.vertical, 6)
                                .background(Color(hex: "#38BDF8").opacity(0.2))
                                .foregroundColor(Color(hex: "#38BDF8"))
                                .cornerRadius(8)
                            }
                        }
                    }
                    .padding(14)
                    .background(Color(white: 0.1))
                    .cornerRadius(12)

                    // Controls Row
                    HStack {
                        Menu {
                            ForEach(viewModel.repository.satellites) { sat in
                                Button(action: { viewModel.selectSatellite(sat) }) {
                                    Text(sat.name)
                                }
                            }
                        } label: {
                            HStack {
                                Text("Satellite:")
                                    .font(.caption)
                                    .foregroundColor(.gray)
                                Text(viewModel.activeSatellite.name)
                                    .font(.caption)
                                    .fontWeight(.bold)
                                    .foregroundColor(.white)
                                Image(systemName: "chevron.down")
                                    .font(.caption2)
                            }
                            .padding(.horizontal, 10)
                            .padding(.vertical, 6)
                            .background(Color(white: 0.12))
                            .cornerRadius(8)
                        }

                        Spacer()

                        Picker("Min Elevation", selection: $viewModel.minElevationFilterDeg) {
                            Text("10° Horizon").tag(10.0)
                            Text("20° Clear").tag(20.0)
                            Text("30° High").tag(30.0)
                            Text("45° Direct").tag(45.0)
                        }
                        .pickerStyle(.menu)
                        .onChange(of: viewModel.minElevationFilterDeg) { _ in
                            viewModel.recomputePasses()
                        }
                    }

                    // Passes List
                    if viewModel.upcomingPasses.isEmpty {
                        VStack(spacing: 12) {
                            Text("🛰️")
                                .font(.system(size: 40))
                            Text("No visible passes above \(Int(viewModel.minElevationFilterDeg))° in the next 24 hours.")
                                .font(.subheadline)
                                .foregroundColor(.gray)
                                .multilineTextAlignment(.center)
                        }
                        .padding(.vertical, 40)
                    } else {
                        ForEach(Array(viewModel.upcomingPasses.enumerated()), id: \.offset) { index, pass in
                            PassCardView(pass: pass, index: index + 1)
                        }
                    }
                }
                .padding()
            }
            .navigationTitle("Pass Predictor")
            .background(Color.black.edgesIgnoringSafeArea(.all))
        }
    }
}

private struct PassCardView: View {
    let pass: PassPrediction
    let index: Int

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Text("\(pass.satName) • Pass #\(index)")
                    .font(.subheadline)
                    .fontWeight(.bold)
                    .foregroundColor(.white)
                Spacer()
                Text(pass.quality)
                    .font(.system(size: 10, weight: .bold))
                    .padding(.horizontal, 8)
                    .padding(.vertical, 3)
                    .background(qualityColor.opacity(0.2))
                    .foregroundColor(qualityColor)
                    .cornerRadius(4)
            }

            HStack {
                VStack(alignment: .leading, spacing: 2) {
                    Text("AOS (START)")
                        .font(.system(size: 9, weight: .bold))
                        .foregroundColor(.gray)
                    Text(formatTime(pass.aosTimeMs))
                        .font(.system(size: 13, weight: .semibold, design: .monospaced))
                        .foregroundColor(.white)
                }

                Spacer()

                VStack(alignment: .leading, spacing: 2) {
                    Text("MAX ELEVATION")
                        .font(.system(size: 9, weight: .bold))
                        .foregroundColor(.gray)
                    Text("\(pass.maxElevDeg, specifier: "%.0f")° @ \(PassPredictorEngine.azimuthToCompassDirection(pass.maxAzimuthDeg))")
                        .font(.system(size: 13, weight: .bold, design: .monospaced))
                        .foregroundColor(qualityColor)
                }

                Spacer()

                VStack(alignment: .leading, spacing: 2) {
                    Text("DURATION")
                        .font(.system(size: 9, weight: .bold))
                        .foregroundColor(.gray)
                    Text("\(pass.durationSec / 60)m \(pass.durationSec % 60)s")
                        .font(.system(size: 13, weight: .semibold, design: .monospaced))
                        .foregroundColor(.white)
                }
            }

            HStack {
                Text("Trajectory: \(PassPredictorEngine.azimuthToCompassDirection(pass.aosAzimuthDeg)) → \(PassPredictorEngine.azimuthToCompassDirection(pass.maxAzimuthDeg)) → \(PassPredictorEngine.azimuthToCompassDirection(pass.losAzimuthDeg))")
                    .font(.caption2)
                    .foregroundColor(.gray)
                Spacer()
                Text(countdownString(pass.aosTimeMs))
                    .font(.caption2)
                    .fontWeight(.bold)
                    .foregroundColor(Color(hex: "#38BDF8"))
            }
        }
        .padding(14)
        .background(Color(white: 0.08))
        .cornerRadius(12)
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .stroke(Color.white.opacity(0.08), lineWidth: 1)
        )
    }

    private var qualityColor: Color {
        switch pass.quality {
        case "EXCELLENT": return Color.green
        case "GOOD": return Color.blue
        default: return Color.orange
        }
    }

    private func formatTime(_ ms: Int64) -> String {
        let date = Date(timeIntervalSince1970: TimeInterval(ms) / 1000.0)
        let formatter = DateFormatter()
        formatter.dateFormat = "MMM d, HH:mm"
        return formatter.string(from: date)
    }

    private func countdownString(_ ms: Int64) -> String {
        let diffSec = Int((Double(ms) / 1000.0) - Date().timeIntervalSince1970)
        if diffSec <= 0 { return "Live Now" }
        let hours = diffSec / 3600
        let minutes = (diffSec % 3600) / 60
        return hours > 0 ? "In \(hours)h \(minutes)m" : "In \(minutes)m"
    }
}
