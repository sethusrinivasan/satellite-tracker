using Microsoft.UI.Xaml.Controls;
using SatTrack.Windows.Services;

namespace SatTrack.Windows.Views;

public sealed partial class GlobePage : Page
{
    private readonly SatelliteRepository _repository = new();

    public GlobePage()
    {
        this.InitializeComponent();
        var sat = _repository.Satellites[0];
        var state = Sgp4Engine.Propagate(sat);
        TxtGlobeTelemetry.Text = $"{state.Name} (NORAD {state.Id})\nLat: {state.LatDeg:F2}° | Lng: {state.LngDeg:F2}° | Alt: {state.AltKm:F0} km | Vel: {state.VelKmS:F2} km/s";
    }
}
