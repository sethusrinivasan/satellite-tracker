using System;

namespace SatTrack.Windows.Models;

/// <summary>
/// Core satellite entity representing a parsed Two-Line Element (TLE) set.
/// </summary>
public record SatelliteEntity(
    int Id,
    string Name,
    string Category,
    string Line1,
    string Line2,
    string IntlDesignator = "",
    string OrbitType = "LEO",
    double InclinationDeg = 0.0,
    double AltitudeKm = 400.0,
    double PeriodMin = 90.0,
    bool IsTracked = false,
    string ColorHex = "#38BDF8"
);

/// <summary>
/// Instantaneous sub-satellite point and orbital telemetry state.
/// </summary>
public record SatelliteState(
    int Id,
    string Name,
    double LatDeg,
    double LngDeg,
    double AltKm,
    double VelKmS,
    double VelMph,
    double FootprintKm,
    double InclinationDeg,
    double PeriodMin,
    string OrbitType,
    string ColorHex,
    long TimestampMs
);

/// <summary>
/// Ground station observer coordinates for look-angles and pass calculation.
/// </summary>
public record ObserverLocation(
    double LatDeg = 37.7749,
    double LngDeg = -122.4194,
    double AltKm = 0.03,
    string Name = "Observer (San Francisco)"
);

/// <summary>
/// Calculated upcoming pass schedule and look-angles.
/// </summary>
public record PassPrediction(
    int SatId,
    string SatName,
    long AosTimeMs,
    double AosAzimuthDeg,
    double MaxElevDeg,
    long MaxElevTimeMs,
    double MaxAzimuthDeg,
    long LosTimeMs,
    double LosAzimuthDeg,
    long DurationSec,
    string Quality
);
