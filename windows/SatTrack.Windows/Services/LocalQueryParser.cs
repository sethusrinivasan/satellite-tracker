using System;
using System.Collections.Generic;
using System.Linq;
using SatTrack.Windows.Models;

namespace SatTrack.Windows.Services;

/// <summary>
/// Natural Language and Semantic Query Parser in C# for offline orbital discovery.
/// </summary>
public static class LocalQueryParser
{
    public record QueryResult(string Text, List<SatelliteEntity> MatchedSatellites);

    public static QueryResult ParseQuery(string query, List<SatelliteEntity> catalog)
    {
        string q = query.Trim().ToLowerInvariant();

        // 1. Space stations
        if (q.Contains("station") || q.Contains("iss") || q.Contains("crew") || q.Contains("tiangong"))
        {
            var sats = catalog.Where(s => s.Category == "stations" || s.Id == 25544 || s.Id == 48274).ToList();
            string lines = string.Join("\n", sats.Select(s => $"• {s.Name} (NORAD {s.Id}) — Alt: {(int)s.AltitudeKm} km, Inc: {s.InclinationDeg}°"));
            return new QueryResult(
                $"Detected {sats.Count} continuously inhabited space stations in Low Earth Orbit (LEO):\n{lines}\n\nBoth stations operate at ~7.6 km/s (~17,100 mph) with 92-minute orbital periods.",
                sats
            );
        }

        // 2. Weather & Earth observation
        if (q.Contains("weather") || q.Contains("climate") || q.Contains("earth") || q.Contains("storm"))
        {
            var sats = catalog.Where(s => s.Category == "weather" || s.Category == "earth").Take(4).ToList();
            string lines = string.Join("\n", sats.Select(s => $"• {s.Name} [{s.OrbitType}] — Alt: {(int)s.AltitudeKm} km, Inc: {s.InclinationDeg}°"));
            return new QueryResult(
                $"Identified {sats.Count} meteorological & Earth observation satellites in Sun-Synchronous and Geostationary orbits:\n{lines}",
                sats
            );
        }

        // 3. Navigation / GPS / GNSS
        if (q.Contains("gps") || q.Contains("navigation") || q.Contains("galileo") || q.Contains("glonass"))
        {
            var sats = catalog.Where(s => s.Category == "gps").Take(4).ToList();
            string lines = string.Join("\n", sats.Select(s => $"• {s.Name} (NORAD {s.Id}) — Alt: {(int)s.AltitudeKm} km, Period: {(int)s.PeriodMin} min"));
            return new QueryResult(
                $"Found {sats.Count} Global Navigation Satellite System (GNSS) spacecraft in Medium Earth Orbit:\n{lines}\n\nThese satellites orbit twice per sidereal day at ~20,200 km altitude.",
                sats
            );
        }

        // 4. Starlink / Constellations
        if (q.Contains("starlink") || q.Contains("constellation") || q.Contains("internet") || q.Contains("iridium"))
        {
            var sats = catalog.Where(s => s.Category == "starlink").Take(4).ToList();
            string lines = string.Join("\n", sats.Select(s => $"• {s.Name} — Alt: {(int)s.AltitudeKm} km, Orbit: {s.OrbitType}"));
            return new QueryResult(
                $"Found {sats.Count} broadband communication constellation satellites in 53°–86° inclination shells:\n{lines}",
                sats
            );
        }

        // 5. Scientific / Telescopes
        if (q.Contains("science") || q.Contains("telescope") || q.Contains("hubble") || q.Contains("astronomy"))
        {
            var sats = catalog.Where(s => s.Category == "science" || s.Id == 20580).ToList();
            string lines = string.Join("\n", sats.Select(s => $"• {s.Name} — Alt: {(int)s.AltitudeKm} km, Period: {(int)s.PeriodMin} min"));
            return new QueryResult(
                $"Found {sats.Count} space astronomy and orbital observatories:\n{lines}",
                sats
            );
        }

        // 6. Generic filter or fallback
        var matches = catalog.Where(s => s.Name.Contains(q, StringComparison.OrdinalIgnoreCase)).Take(5).ToList();
        if (matches.Count > 0)
        {
            string lines = string.Join("\n", matches.Select(s => $"• {s.Name} (NORAD {s.Id}) — Orbit: {s.OrbitType}"));
            return new QueryResult(
                $"Matched {matches.Count} satellites matching query '{query}':\n{lines}",
                matches
            );
        }

        return new QueryResult(
            $"No direct catalog match for '{query}'. Try searching for:\n• 'Space stations'\n• 'GPS navigation satellites'\n• 'Weather and storm trackers'\n• 'Starlink internet constellation'\n• 'Hubble Space Telescope'",
            new List<SatelliteEntity>()
        );
    }
}
