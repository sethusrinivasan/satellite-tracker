import Foundation
import CoreLocation
import Combine

/// CoreLocation service for obtaining current observer coordinates for pass predictions.
public final class LocationService: NSObject, ObservableObject, CLLocationManagerDelegate {

    public static let shared = LocationService()

    @Published public var observer = ObserverLocation()
    @Published public var authorizationStatus: CLAuthorizationStatus = .notDetermined
    @Published public var isLocating: Bool = false
    @Published public var locationError: String? = nil

    private let manager = CLLocationManager()

    public override init() {
        super.init()
        manager.delegate = self
        manager.desiredAccuracy = kCLLocationAccuracyHundredMeters
        authorizationStatus = manager.authorizationStatus
    }

    public func requestLocation() {
        isLocating = true
        locationError = nil
        if authorizationStatus == .notDetermined {
            manager.requestWhenInUseAuthorization()
        } else if authorizationStatus == .authorizedWhenInUse || authorizationStatus == .authorizedAlways {
            manager.requestLocation()
        } else {
            isLocating = false
            locationError = "Location access denied. Using manual coordinates."
        }
    }

    // MARK: - CLLocationManagerDelegate

    public func locationManagerDidChangeAuthorization(_ manager: CLLocationManager) {
        authorizationStatus = manager.authorizationStatus
        if authorizationStatus == .authorizedWhenInUse || authorizationStatus == .authorizedAlways {
            manager.requestLocation()
        }
    }

    public func locationManager(_ manager: CLLocationManager, didUpdateLocations locations: [CLLocation]) {
        isLocating = false
        guard let loc = locations.last else { return }

        let lat = (loc.coordinate.latitude * 1000.0).rounded() / 1000.0
        let lng = (loc.coordinate.longitude * 1000.0).rounded() / 1000.0
        let altKm = max(0.01, loc.altitude / 1000.0)

        observer = ObserverLocation(
            latDeg: lat,
            lngDeg: lng,
            altKm: altKm,
            name: "My GPS Device Location"
        )
    }

    public func locationManager(_ manager: CLLocationManager, didFailWithError error: Error) {
        isLocating = false
        locationError = error.localizedDescription
    }
}
