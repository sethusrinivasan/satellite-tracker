// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "SatTrack",
    platforms: [
        .iOS(.v16),
        .macOS(.v13)
    ],
    products: [
        .library(
            name: "SatTrackCore",
            targets: ["SatTrackCore"]
        )
    ],
    targets: [
        .target(
            name: "SatTrackCore",
            path: "SatTrack",
            exclude: ["Info.plist"]
        ),
        .testTarget(
            name: "SatTrackCoreTests",
            dependencies: ["SatTrackCore"],
            path: "Tests"
        )
    ]
)
