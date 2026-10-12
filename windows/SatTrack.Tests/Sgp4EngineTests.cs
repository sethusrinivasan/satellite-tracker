using System;
using System.Collections.Generic;
using SatTrack.Windows.Models;
using SatTrack.Windows.Services;
using Xunit;

namespace SatTrack.Tests;

public class Sgp4EngineTests
{
    [Fact]
    public void TestIssPropagation()
    {
        var iss = new SatelliteEntity(
            25544,
            "ISS (ZARYA)",
            "stations",
            "1 25544U 98067A   24095.53472222  .00016717  00000-0  10270-3 0  9002",
            "2 25544  51.6416 247.4627 0006703 130.5360 325.0288 15.49887754447413"
        );

        var state = Sgp4Engine.Propagate(iss);
        Assert.Equal(25544, state.Id);
        Assert.InRange(state.LatDeg, -52.0, 52.0);
        Assert.InRange(state.AltKm, 350.0, 460.0);
        Assert.True(state.VelKmS > 7.0);
    }

    [Fact]
    public void TestPassPredictorLookAngles()
    {
        var observer = new ObserverLocation(37.7749, -122.4194, 0.03);
        // Spacecraft directly overhead
        var look = PassPredictorEngine.CalculateLookAngles(
            observer,
            37.7749,
            -122.4194,
            420.0
        );

        Assert.True(look.ElevationDeg > 85.0);
        Assert.True(look.ElevationDeg <= 90.0);
        Assert.True(Math.Abs(look.RangeKm - 420.0) < 2.0);
    }

    [Fact]
    public void TestLocalQueryParser()
    {
        var catalog = new List<SatelliteEntity>
        {
            new(25544, "ISS (ZARYA)", "stations", "", ""),
            new(48859, "GPS III-05", "gps", "", "")
        };

        var stationRes = LocalQueryParser.ParseQuery("Where is the space station?", catalog);
        Assert.Contains("inhabited space stations", stationRes.Text);
        Assert.Equal(25544, stationRes.MatchedSatellites[0].Id);

        var gpsRes = LocalQueryParser.ParseQuery("GPS navigation", catalog);
        Assert.Contains("GNSS", gpsRes.Text);
        Assert.Equal(48859, gpsRes.MatchedSatellites[0].Id);
    }
}
