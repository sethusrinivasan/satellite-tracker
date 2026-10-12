import SwiftUI

/// AI Orbital Discovery View for natural language satellite search.
public struct AiDiscoveryView: View {
    @EnvironmentObject var viewModel: SatelliteViewModel

    private let suggestions = [
        "Inhabited space stations",
        "GPS navigation satellites",
        "Weather & storm observation",
        "Starlink internet constellation",
        "Hubble Space Telescope"
    ]

    public init() {}

    public var body: some View {
        NavigationView {
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    // Header Card
                    VStack(alignment: .leading, spacing: 6) {
                        HStack {
                            Text("✨")
                                .font(.title2)
                            Text("Orbital Discovery Assistant")
                                .font(.headline)
                                .foregroundColor(.white)
                        }
                        Text("Search satellites using natural language. Query orbital regimes, constellations, or missions offline.")
                            .font(.caption)
                            .foregroundColor(.gray)
                    }
                    .padding(14)
                    .background(Color(white: 0.1))
                    .cornerRadius(12)

                    // Suggestion Chips
                    ScrollView(.horizontal, showsIndicators: false) {
                        HStack(spacing: 8) {
                            ForEach(suggestions, id: \.self) { suggestion in
                                Button(action: {
                                    viewModel.aiQueryText = suggestion
                                    viewModel.executeAiQuery(suggestion)
                                }) {
                                    Text(suggestion)
                                        .font(.caption)
                                        .padding(.horizontal, 12)
                                        .padding(.vertical, 6)
                                        .background(Color(white: 0.15))
                                        .foregroundColor(Color(hex: "#38BDF8"))
                                        .cornerRadius(16)
                                }
                            }
                        }
                    }

                    // Query Input Field
                    HStack {
                        TextField("e.g. 'Show satellites over 50 degree inclination'", text: $viewModel.aiQueryText)
                            .foregroundColor(.white)
                            .onSubmit { viewModel.executeAiQuery() }

                        Button(action: { viewModel.executeAiQuery() }) {
                            if viewModel.isAiLoading {
                                ProgressView().scaleEffect(0.8)
                            } else {
                                Image(systemName: "arrow.up.circle.fill")
                                    .font(.title2)
                                    .foregroundColor(Color(hex: "#38BDF8"))
                            }
                        }
                    }
                    .padding(12)
                    .background(Color(white: 0.12))
                    .cornerRadius(12)

                    // Response Card
                    VStack(alignment: .leading, spacing: 10) {
                        HStack {
                            Text("RESPONSE")
                                .font(.system(size: 10, weight: .bold))
                                .foregroundColor(.gray)
                            Spacer()
                        }

                        Text(viewModel.aiResponseText)
                            .font(.subheadline)
                            .foregroundColor(.white)
                            .lineSpacing(4)
                    }
                    .padding(14)
                    .background(Color(white: 0.08))
                    .cornerRadius(12)
                    .overlay(
                        RoundedRectangle(cornerRadius: 12)
                            .stroke(Color.white.opacity(0.08), lineWidth: 1)
                    )

                    // Matched Satellites Quick Select
                    if !viewModel.aiMatchedSats.isEmpty {
                        Text("MATCHED SATELLITES")
                            .font(.system(size: 10, weight: .bold))
                            .foregroundColor(.gray)
                            .padding(.top, 8)

                        ForEach(viewModel.aiMatchedSats) { sat in
                            HStack {
                                Circle()
                                    .fill(Color(hex: sat.colorHex))
                                    .frame(width: 8, height: 8)
                                Text(sat.name)
                                    .font(.subheadline)
                                    .fontWeight(.semibold)
                                    .foregroundColor(.white)
                                Spacer()
                                Button(action: { viewModel.selectSatellite(sat) }) {
                                    Text("Track")
                                        .font(.caption)
                                        .fontWeight(.bold)
                                        .padding(.horizontal, 12)
                                        .padding(.vertical, 4)
                                        .background(Color(hex: "#38BDF8").opacity(0.2))
                                        .foregroundColor(Color(hex: "#38BDF8"))
                                        .cornerRadius(6)
                                }
                            }
                            .padding(12)
                            .background(Color(white: 0.1))
                            .cornerRadius(8)
                        }
                    }
                }
                .padding()
            }
            .navigationTitle("AI Assistant")
            .background(Color.black.edgesIgnoringSafeArea(.all))
        }
    }
}
