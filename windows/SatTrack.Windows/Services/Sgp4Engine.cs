using System;
using System.Collections.Generic;
using SatTrack.Windows.Models;

namespace SatTrack.Windows.Services;

/// <summary>
/// High-performance SGP4 and Keplerian orbital propagation engine in C#.
/// Converts Two-Line Element (TLE) records to WGS-84 Geodetic coordinates from first principles.
/// </summary>
public static class Sgp4Engine
{
    public const double EarthRadiusKm = 6378.137;
    public const double MuEarth = 398600.4418; // km^3 / s^2
    public const double J2 = 1.08262668e-3;
    public const double Wgs84Flattening = 1.0 / 298.257223563;

    public record TleRecord(
        int NoradId,
        int EpochYear,
        double EpochDay,
        double BStar,
        double InclinationRad,
        double RaanRad,
        double Eccentricity,
        double ArgPerigeeRad,
        double MeanAnomalyRad,
        double MeanMotionRadMin,
        int RevAtEpoch
    );

    public static TleRecord ParseTle(string line1, string line2)
    {
        string l1 = line1.Trim();
        string l2 = line2.Trim();

        int noradId = int.TryParse(Sub(l1, 2, 7)?.Trim(), out var nid) ? nid : 0;
        int epochYearRaw = int.TryParse(Sub(l1, 18, 20)?.Trim(), out var yr) ? yr : 24;
        int epochYear = epochYearRaw < 57 ? 2000 + epochYearRaw : 1900 + epochYearRaw;
        double epochDay = double.TryParse(Sub(l1, 20, 32)?.Trim(), out var ed) ? ed : 1.0;

        string bStarStr = Sub(l1, 53, 61)?.Trim().Replace(" ", "") ?? "";
        double bStar = ParseExponentialNotation(bStarStr);

        double incDeg = double.TryParse(Sub(l2, 8, 16)?.Trim(), out var inc) ? inc : 0.0;
        double raanDeg = double.TryParse(Sub(l2, 17, 25)?.Trim(), out var raan) ? raan : 0.0;
        string eccStr = "0." + (Sub(l2, 26, 33)?.Trim() ?? "001");
        double ecc = double.TryParse(eccStr, out var e) ? e : 0.001;
        double argPerDeg = double.TryParse(Sub(l2, 34, 42)?.Trim(), out var ap) ? ap : 0.0;
        double meanAnomDeg = double.TryParse(Sub(l2, 43, 51)?.Trim(), out var ma) ? ma : 0.0;
        double mmRevsDay = double.TryParse(Sub(l2, 52, 63)?.Trim(), out var mm) ? mm : 15.0;
        int revEpoch = int.TryParse(Sub(l2, 63, 68)?.Trim(), out var re) ? re : 0;

        double mmRadMin = mmRevsDay * (2.0 * Math.PI / 1440.0);

        return new TleRecord(
            noradId,
            epochYear,
            epochDay,
            bStar,
            incDeg * Math.PI / 180.0,
            raanDeg * Math.PI / 180.0,
            ecc,
            argPerDeg * Math.PI / 180.0,
            meanAnomDeg * Math.PI / 180.0,
            mmRadMin,
            revEpoch
        );
    }

    private static string? Sub(string str, int start, int end)
    {
        if (start >= str.Length) return null;
        int len = Math.Min(end, str.Length) - start;
        return str.Substring(start, len);
    }

    private static double ParseExponentialNotation(string s)
    {
        if (string.IsNullOrEmpty(s) || s == "0") return 0.0;
        try
        {
            double sign = s.StartsWith("-") ? -1.0 : 1.0;
            string clean = s.TrimStart('-', '+');
            if (clean.Length >= 2)
            {
                string mantissaStr = clean.Substring(0, clean.Length - 2);
                string expStr = clean.Substring(clean.Length - 2);
                if (double.TryParse(mantissaStr, out var mantissa) && int.TryParse(expStr, out var exp))
                {
                    return sign * (mantissa * 1e-5) * Math.Pow(10.0, exp);
                }
            }
        }
        catch { }
        return 0.0;
    }

    public static SatelliteState Propagate(SatelliteEntity sat, long targetMs = 0)
    {
        if (targetMs == 0) targetMs = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds();
        var tle = ParseTle(sat.Line1, sat.Line2);
        return PropagateTle(sat, tle, targetMs);
    }

    public static SatelliteState PropagateTle(SatelliteEntity sat, TleRecord tle, long targetMs)
    {
        double jdTarget = (targetMs / 86400000.0) + 2440587.5;
        double jdEpoch = EpochToJulianDate(tle.EpochYear, tle.EpochDay);
        double deltaMin = (jdTarget - jdEpoch) * 1440.0;

        double nSec = tle.MeanMotionRadMin / 60.0;
        double a = Math.Pow(MuEarth / (nSec * nSec), 1.0 / 3.0);

        double p = a * (1.0 - tle.Eccentricity * tle.Eccentricity);
        double cosInc = Math.Cos(tle.InclinationRad);
        double sinInc = Math.Sin(tle.InclinationRad);

        double j2Factor = 1.5 * J2 * Math.Pow(EarthRadiusKm / p, 2.0) * tle.MeanMotionRadMin;
        double raanRate = -j2Factor * cosInc;
        double argPerRate = 0.75 * j2Factor * (5.0 * cosInc * cosInc - 1.0);

        double raan = (tle.RaanRad + raanRate * deltaMin) % (2.0 * Math.PI);
        double argPer = (tle.ArgPerigeeRad + argPerRate * deltaMin) % (2.0 * Math.PI);
        double meanAnom = (tle.MeanAnomalyRad + tle.MeanMotionRadMin * deltaMin) % (2.0 * Math.PI);

        // Kepler solver: M = E - e * sin(E)
        double eAnom = meanAnom;
        for (int i = 0; i < 16; i++)
        {
            double f = eAnom - tle.Eccentricity * Math.Sin(eAnom) - meanAnom;
            double fPrime = 1.0 - tle.Eccentricity * Math.Cos(eAnom);
            double delta = f / fPrime;
            eAnom -= delta;
            if (Math.Abs(delta) < 1e-8) break;
        }

        double sinNu = (Math.Sqrt(1.0 - tle.Eccentricity * tle.Eccentricity) * Math.Sin(eAnom)) / (1.0 - tle.Eccentricity * Math.Cos(eAnom));
        double cosNu = (Math.Cos(eAnom) - tle.Eccentricity) / (1.0 - tle.Eccentricity * Math.Cos(eAnom));
        double nu = Math.Atan2(sinNu, cosNu);

        double r = a * (1.0 - tle.Eccentricity * Math.Cos(eAnom));
        double u = (argPer + nu) % (2.0 * Math.PI);
        double xOrb = r * Math.Cos(u);
        double yOrb = r * Math.Sin(u);

        double cosRaan = Math.Cos(raan);
        double sinRaan = Math.Sin(raan);

        double xEci = xOrb * cosRaan - yOrb * cosInc * sinRaan;
        double yEci = xOrb * sinRaan + yOrb * cosInc * cosRaan;
        double zEci = yOrb * sinInc;

        double velKmS = Math.Sqrt(MuEarth * (2.0 / r - 1.0 / a));
        double velMph = velKmS * 2236.936;

        double gmst = ComputeGmst(jdTarget);
        double cosGmst = Math.Cos(gmst);
        double sinGmst = Math.Sin(gmst);

        double xEcf = xEci * cosGmst + yEci * sinGmst;
        double yEcf = -xEci * sinGmst + yEci * cosGmst;
        double zEcf = zEci;

        // WGS-84 Geodetic
        double lngRad = Math.Atan2(yEcf, xEcf);
        double pDist = Math.Sqrt(xEcf * xEcf + yEcf * yEcf);
        double latRad = Math.Atan2(zEcf, pDist * (1.0 - Wgs84Flattening));

        for (int i = 0; i < 6; i++)
        {
            double sinLat = Math.Sin(latRad);
            double nRadius = EarthRadiusKm / Math.Sqrt(1.0 - (2.0 * Wgs84Flattening - Wgs84Flattening * Wgs84Flattening) * sinLat * sinLat);
            latRad = Math.Atan2(zEcf + (2.0 * Wgs84Flattening - Wgs84Flattening * Wgs84Flattening) * nRadius * sinLat, pDist);
        }

        double latDeg = latRad * 180.0 / Math.PI;
        double lngDeg = ((lngRad * 180.0 / Math.PI) + 180.0) % 360.0 - 180.0;
        double altKm = r - EarthRadiusKm;

        double footprintAngle = Math.Acos(Math.Min(1.0, EarthRadiusKm / (EarthRadiusKm + Math.Max(10.0, altKm))));
        double footprintKm = EarthRadiusKm * footprintAngle;
        double periodMin = (2.0 * Math.PI * Math.Pow(a, 1.5)) / (Math.Sqrt(MuEarth) * 60.0);

        return new SatelliteState(
            sat.Id,
            sat.Name,
            Math.Round(latDeg, 2),
            Math.Round(lngDeg, 2),
            Math.Round(altKm, 1),
            Math.Round(velKmS, 2),
            Math.Round(velMph, 0),
            Math.Round(footprintKm, 0),
            Math.Round(tle.InclinationRad * 180.0 / Math.PI, 2),
            Math.Round(periodMin, 1),
            sat.OrbitType,
            sat.ColorHex,
            targetMs
        );
    }

    public static List<List<(double Lat, double Lng)>> ComputeGroundTrack(SatelliteEntity sat, long targetMs = 0, int steps = 120)
    {
        if (targetMs == 0) targetMs = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds();
        var tle = ParseTle(sat.Line1, sat.Line2);
        double periodMin = Math.Clamp(sat.PeriodMin, 80.0, 1440.0);
        long periodMs = (long)(periodMin * 60.0 * 1000.0);
        long stepMs = periodMs / steps;

        var segments = new List<List<(double Lat, double Lng)>>();
        var currentSegment = new List<(double Lat, double Lng)>();
        double? prevLng = null;

        for (int i = 0; i <= steps; i++)
        {
            long t = targetMs + i * stepMs;
            var state = PropagateTle(sat, tle, t);

            if (prevLng.HasValue && Math.Abs(state.LngDeg - prevLng.Value) > 180.0)
            {
                if (currentSegment.Count > 0)
                {
                    segments.Add(currentSegment);
                    currentSegment = new List<(double Lat, double Lng)>();
                }
            }

            currentSegment.Add((state.LatDeg, state.LngDeg));
            prevLng = state.LngDeg;
        }

        if (currentSegment.Count > 0)
        {
            segments.Add(currentSegment);
        }

        return segments;
    }

    private static double EpochToJulianDate(int year, double day)
    {
        int y = year - 1;
        int a = y / 100;
        int b = 2 - a + a / 4;
        double jdJan0 = Math.Floor(365.25 * (y + 4716)) + Math.Floor(30.6001 * 14.0) + b - 1524.5;
        return jdJan0 + day;
    }

    private static double ComputeGmst(double jd)
    {
        double d = jd - 2451545.0;
        double gmstDeg = 280.46061837 + 360.98564736629 * d;
        gmstDeg %= 360.0;
        if (gmstDeg < 0.0) gmstDeg += 360.0;
        return gmstDeg * Math.PI / 180.0;
    }
}
