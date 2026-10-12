import SwiftUI

/// Main Root Tab navigation for the native iOS application.
public struct RootTabView: View {
    @StateObject private var viewModel = SatelliteViewModel()

    public init() {}

    public var body: some View {
        TabView {
            TrackerView()
                .tabItem {
                    Label("2D Tracker", systemImage: "map")
                }

            Globe3DView()
                .tabItem {
                    Label("3D Globe", systemImage: "globe.americas.fill")
                }

            PassesView()
                .tabItem {
                    Label("Passes", systemImage: "binoculars.fill")
                }

            CatalogView()
                .tabItem {
                    Label("Catalog", systemImage: "list.bullet")
                }

            AiDiscoveryView()
                .tabItem {
                    Label("AI Discovery", systemImage: "sparkles")
                }
        }
        .environmentObject(viewModel)
        .accentColor(Color(hex: "#38BDF8"))
        .preferredColorScheme(.dark)
    }
}

// MARK: - Color Hex Extension
extension Color {
    init(hex: String) {
        let hex = hex.trimmingCharacters(in: CharacterSet.alphanumerics.inverted)
        var int: UInt64 = 0
        Scanner(string: hex).scanHexInt64(&int)
        let a, r, g, b: UInt64
        switch hex.count {
        case 3: // RGB (12-bit)
            (a, r, g, b) = (255, (int >> 8) * 17, (int >> 4 & 0xF) * 17, (int & 0xF) * 17)
        case 6: // RGB (24-bit)
            (a, r, g, b) = (255, int >> 16, int >> 8 & 0xFF, int & 0xFF)
        case 8: // ARGB (32-bit)
            (a, r, g, b) = (int >> 24, int >> 16 & 0xFF, int >> 8 & 0xFF, int & 0xFF)
        default:
            (a, r, g, b) = (1, 1, 1, 0)
        }
        self.init(
            .sRGB,
            red: Double(r) / 255,
            green: Double(g) / 255,
            blue:  Double(b) / 255,
            opacity: Double(a) / 255
        )
    }
}
