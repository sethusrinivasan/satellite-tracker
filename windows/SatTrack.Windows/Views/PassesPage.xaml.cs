using System;
using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using SatTrack.Windows.Models;
using SatTrack.Windows.Services;

namespace SatTrack.Windows.Views;

public sealed partial class PassesPage : Page
{
    private readonly SatelliteRepository _repository = new();
    private readonly LocationService _locationService = new();
    private SatelliteEntity _activeSat;
    private ObserverLocation _observer;

    public PassesPage()
    {
        this.InitializeComponent();
        _activeSat = _repository.Satellites[0];
        _observer = _locationService.Observer;

        foreach (var s in _repository.Satellites)
        {
            SatPassSelector.Items.Add(s.Name);
        }
        SatPassSelector.SelectedIndex = 0;

        UpdateObserverDisplay();
        RecomputePasses();
    }

    private void UpdateObserverDisplay()
    {
        TxtObserverName.Text = _observer.Name;
        TxtObserverCoords.Text = $"{_observer.LatDeg:F3}° N, {_observer.LngDeg:F3}° E";
    }

    private void RecomputePasses()
    {
        double minElev = 10.0;
        if (CmbMinElev.SelectedItem is ComboBoxItem item && double.TryParse(item.Tag?.ToString(), out var el))
        {
            minElev = el;
        }

        var passes = PassPredictorEngine.PredictPasses(_activeSat, _observer, minElev);
        ListPasses.ItemsSource = passes;
    }

    private async void BtnGps_Click(object sender, RoutedEventArgs e)
    {
        BtnGps.IsEnabled = false;
        BtnGps.Content = "📍 Locating...";
        _observer = await _locationService.RequestLocationAsync();
        UpdateObserverDisplay();
        RecomputePasses();
        BtnGps.Content = "📍 Location Updated";
        BtnGps.IsEnabled = true;
    }

    private void SatPassSelector_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (SatPassSelector.SelectedIndex >= 0 && SatPassSelector.SelectedIndex < _repository.Satellites.Count)
        {
            _activeSat = _repository.Satellites[SatPassSelector.SelectedIndex];
            RecomputePasses();
        }
    }

    private void CmbMinElev_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        RecomputePasses();
    }
}
