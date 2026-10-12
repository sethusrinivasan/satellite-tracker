using System;
using System.Collections.Generic;
using SatTrack.Windows.Models;

namespace SatTrack.Windows.Services;

/// <summary>
/// Topocentric Look-Angles and Overpass Prediction Engine in C#.
/// </summary>
public static class PassPredictorEngine
{
    public record LookAngles(double AzimuthDeg, double ElevationDeg, double RangeKm);

    public static LookAngles CalculateLookAngles(
        ObserverLocation observer,
        double satLatDeg,
        double satLngDeg,
        double satAltKm)
    {
        double obsLatRad = observer.LatDeg * Math.PI / 180.0;
        double obsLngRad = observer.LngDeg * Math.PI / 180.0;
        double obsR = Sgp4Engine.EarthRadiusKm + observer.AltKm;

        double obsX = obsR * Math.Cos(obsLatRad) * Math.Cos(obsLngRad);
        double obsY = obsR * Math.Cos(obsLatRad) * Math.Sin(obsLngRad);
        double obsZ = obsR * Math.Sin(obsLatRad);

        double satLatRad = satLatDeg * Math.PI / 180.0;
        double satLngRad = satLngDeg * Math.PI / 180.0;
        double satR = Sgp4Engine.EarthRadiusKm + satAltKm;

        double satX = satR * Math.Cos(satLatRad) * Math.Cos(satLngRad);
        double satY = satR * Math.Cos(satLatRad) * Math.Sin(satLngRad);
        double satZ = satR * Math.Sin(satLatRad);

        double dx = satX - obsX;
        double dy = satY - obsY;
        double dz = satZ - obsZ;
        double range = Math.Sqrt(dx * dx + dy * dy + dz * dz);

        double sinLat = Math.Sin(obsLatRad);
        double cosLat = Math.Cos(obsLatRad);
        double sinLng = Math.Sin(obsLngRad);
        double cosLng = Math.Cos(obsLngRad);

        double north = -sinLat * cosLng * dx - sinLat * sinLng * dy + cosLat * dz;
        double east = -sinLng * dx + cosLng * dy;
        double up = cosLat * cosLng * dx + cosLat * sinLng * dy + sinLat * dz;

        double elevationRad = Math.Asin(Math.Clamp(up / range, -1.0, 1.0));
        double azimuthRad = Math.Atan2(east, north);
        if (azimuthRad < 0.0) azimuthRad += 2.0 * Math.PI;

        return new LookAngles(
            azimuthRad * 180.0 / Math.PI,
            elevationRad * 180.0 / Math.PI,
            range
        );
    }

    public static List<PassPrediction> PredictPasses(
        SatelliteEntity sat,
        ObserverLocation observer,
        double minElevationDeg = 10.0,
        int maxPasses = 8)
    {
        var tle = Sgp4Engine.ParseTle(sat.Line1, sat.Line2);
        long nowMs = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds();
        long horizonMs = 86400000; // 24 hours
        long stepMs = 30000; // 30 seconds

        var passes = new List<PassPrediction>();
        bool inPass = false;
        long aosTime = 0;
        double aosAzimuth = 0.0;
        double maxElev = -90.0;
        long maxElevTime = 0;
        double maxAzimuth = 0.0;

        long t = nowMs;
        long endT = nowMs + horizonMs;

        while (t < endT)
        {
            var state = Sgp4Engine.PropagateTle(sat, tle, t);
            var look = CalculateLookAngles(observer, state.LatDeg, state.LngDeg, state.AltKm);

            if (look.ElevationDeg >= minElevationDeg)
            {
                if (!inPass)
                {
                    inPass = true;
                    aosTime = t;
                    aosAzimuth = look.AzimuthDeg;
                    maxElev = look.ElevationDeg;
                    maxElevTime = t;
                    maxAzimuth = look.AzimuthDeg;
                }
                else
                {
                    if (look.ElevationDeg > maxElev)
                    {
                        maxElev = look.ElevationDeg;
                        maxElevTime = t;
                        maxAzimuth = look.AzimuthDeg;
                    }
                }
            }
            else if (inPass)
            {
                inPass = false;
                long losTime = t;
                double losAzimuth = look.AzimuthDeg;
                long durationSec = (losTime - aosTime) / 1000;

                string quality = maxElev >= 60.0 ? "EXCELLENT" : maxElev >= 30.0 ? "GOOD" : "FAIR";

                passes.Add(new PassPrediction(
                    sat.Id,
                    sat.Name,
                    aosTime,
                    Math.Round(aosAzimuth, 1),
                    Math.Round(maxElev, 1),
                    maxElevTime,
                    Math.Round(maxAzimuth, 1),
                    losTime,
                    Math.Round(losAzimuth, 1),
                    durationSec,
                    quality
                ));

                if (passes.Count >= maxPasses) break;
            }

            t += stepMs;
        }

        return passes;
    }

    public static string AzimuthToCompassDirection(double degrees)
    {
        string[] directions = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"];
        int index = (int)(((degrees % 360.0 + 360.0) % 360.0 / 22.5) + 0.5) % 16;
        return directions[index];
    }
}
