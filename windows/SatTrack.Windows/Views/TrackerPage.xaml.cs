using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using SatTrack.Windows.Models;
using SatTrack.Windows.Services;

namespace SatTrack.Windows.Views;

public sealed partial class TrackerPage : Page
{
    private readonly SatelliteRepository _repository = new();
    private SatelliteEntity _activeSat;
    private readonly DispatcherTimer _timer = new() { Interval = System.TimeSpan.FromSeconds(1) };

    public TrackerPage()
    {
        this.InitializeComponent();
        _activeSat = _repository.Satellites[0];

        foreach (var s in _repository.Satellites)
        {
            SatSelector.Items.Add(s.Name);
        }
        SatSelector.SelectedIndex = 0;

        _timer.Tick += (s, e) => UpdateTelemetry();
        _timer.Start();
        UpdateTelemetry();
    }

    private void SatSelector_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (SatSelector.SelectedIndex >= 0 && SatSelector.SelectedIndex < _repository.Satellites.Count)
        {
            _activeSat = _repository.Satellites[SatSelector.SelectedIndex];
            UpdateTelemetry();
        }
    }

    private void UpdateTelemetry()
    {
        var state = Sgp4Engine.Propagate(_activeSat);
        TxtSatName.Text = state.Name;
        TxtNoradMeta.Text = $"NORAD {state.Id} • {state.OrbitType} Orbit";
        TxtLat.Text = $"{state.LatDeg:F2}°";
        TxtLng.Text = $"{state.LngDeg:F2}°";
        TxtAlt.Text = $"{state.AltKm:F1} km";
        TxtVel.Text = $"{state.VelKmS:F2} km/s";
        TxtPeriod.Text = $"{state.PeriodMin:F1} min";
        TxtFootprint.Text = $"{state.FootprintKm:F0} km";
        TxtCoordinates.Text = $"Lat: {state.LatDeg:F2}° | Lng: {state.LngDeg:F2}° | Alt: {state.AltKm:F0} km";
        TxtRawTle.Text = $"{_activeSat.Line1}\n{_activeSat.Line2}";
    }
}
