using System;
using System.Threading.Tasks;
using Windows.Devices.Geolocation;
using SatTrack.Windows.Models;

namespace SatTrack.Windows.Services;

/// <summary>
/// Service providing Windows Geolocation detection for pass predictions.
/// </summary>
public class LocationService
{
    public ObserverLocation Observer { get; private set; } = new();

    public async Task<ObserverLocation> RequestLocationAsync()
    {
        try
        {
            var accessStatus = await Geolocator.RequestAccessAsync();
            if (accessStatus == GeolocationAccessStatus.Allowed)
            {
                var geolocator = new Geolocator { DesiredAccuracy = PositionAccuracy.Default };
                var position = await geolocator.GetGeopositionAsync();
                var coord = position.Coordinate.Point.Position;

                Observer = new ObserverLocation(
                    Math.Round(coord.Latitude, 4),
                    Math.Round(coord.Longitude, 4),
                    Math.Max(0.01, (coord.Altitude) / 1000.0),
                    "My Windows Device Location (GPS)"
                );
            }
        }
        catch
        {
            // Fallback to default
        }

        return Observer;
    }
}
