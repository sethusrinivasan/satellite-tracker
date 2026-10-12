using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Linq;
using System.Threading.Tasks;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using SatTrack.Windows.Models;
using SatTrack.Windows.Services;

namespace SatTrack.Windows.ViewModels;

public partial class SatelliteViewModel : ObservableObject
{
    private readonly SatelliteRepository _repository = new();
    private readonly LocationService _locationService = new();
    private readonly System.Timers.Timer _telemetryTimer = new(1000);

    [ObservableProperty]
    private SatelliteEntity _activeSatellite;

    [ObservableProperty]
    private SatelliteState? _activeState;

    [ObservableProperty]
    private ObserverLocation _observer;

    [ObservableProperty]
    private double _minElevationFilterDeg = 10.0;

    [ObservableProperty]
    private string _aiQueryText = "";

    [ObservableProperty]
    private string _aiResponseText = "Ask anything about active satellites, constellations, orbital inclinations, or pass schedules.";

    [ObservableProperty]
    private bool _isAiLoading;

    [ObservableProperty]
    private string _searchText = "";

    [ObservableProperty]
    private string _selectedCategory = "all";

    public ObservableCollection<SatelliteEntity> Satellites { get; } = new();
    public ObservableCollection<PassPrediction> UpcomingPasses { get; } = new();
    public ObservableCollection<SatelliteEntity> AiMatchedSatellites { get; } = new();

    public SatelliteViewModel()
    {
        _activeSatellite = _repository.Satellites.First();
        _observer = _locationService.Observer;

        foreach (var sat in _repository.Satellites)
        {
            Satellites.Add(sat);
        }

        _telemetryTimer.Elapsed += (s, e) => UpdateTelemetry();
        _telemetryTimer.AutoReset = true;
        _telemetryTimer.Start();

        UpdateTelemetry();
        RecomputePasses();
    }

    [RelayCommand]
    public void SelectSatellite(SatelliteEntity sat)
    {
        ActiveSatellite = sat;
        UpdateTelemetry();
        RecomputePasses();
    }

    [RelayCommand]
    public void ToggleTracking(SatelliteEntity sat)
    {
        _repository.ToggleTracking(sat.Id);
    }

    [RelayCommand]
    public async Task RequestGpsLocationAsync()
    {
        Observer = await _locationService.RequestLocationAsync();
        RecomputePasses();
    }

    [RelayCommand]
    public void ExecuteAiQuery(string? prompt = null)
    {
        string q = prompt ?? AiQueryText;
        if (string.IsNullOrWhiteSpace(q)) return;

        IsAiLoading = true;
        Task.Run(() =>
        {
            var result = LocalQueryParser.ParseQuery(q, _repository.Satellites);
            App.DispatcherQueue.TryEnqueue(() =>
            {
                IsAiLoading = false;
                AiResponseText = result.Text;
                AiMatchedSatellites.Clear();
                foreach (var s in result.MatchedSatellites)
                {
                    AiMatchedSatellites.Add(s);
                }
            });
        });
    }

    public void UpdateTelemetry()
    {
        var state = Sgp4Engine.Propagate(ActiveSatellite);
        if (App.DispatcherQueue != null)
        {
            App.DispatcherQueue.TryEnqueue(() => ActiveState = state);
        }
        else
        {
            ActiveState = state;
        }
    }

    public void RecomputePasses()
    {
        Task.Run(() =>
        {
            var passes = PassPredictorEngine.PredictPasses(ActiveSatellite, Observer, MinElevationFilterDeg);
            App.DispatcherQueue?.TryEnqueue(() =>
            {
                UpcomingPasses.Clear();
                foreach (var p in passes)
                {
                    UpcomingPasses.Add(p);
                }
            });
        });
    }

    public IEnumerable<SatelliteEntity> FilteredCatalog =>
        _repository.Satellites.Where(sat =>
        {
            bool matchesCat = SelectedCategory == "all" || sat.Category == SelectedCategory;
            bool matchesSearch = string.IsNullOrEmpty(SearchText) ||
                                 sat.Name.Contains(SearchText, StringComparison.OrdinalIgnoreCase) ||
                                 sat.Id.ToString().Contains(SearchText);
            return matchesCat && matchesSearch;
        });
}
