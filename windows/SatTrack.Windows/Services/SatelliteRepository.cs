using System.Collections.Generic;
using System.Linq;
using SatTrack.Windows.Models;

namespace SatTrack.Windows.Services;

/// <summary>
/// Repository managing preseeded satellite records and active tracked state.
/// </summary>
public class SatelliteRepository
{
    private static readonly string[] Colors = ["#38BDF8", "#10B981", "#F59E0B", "#A855F7", "#EC4899", "#06B6D4", "#EAB308"];

    public List<SatelliteEntity> Satellites { get; private set; } = new();
    public HashSet<int> TrackedIds { get; private set; } = new([25544, 48274, 20580]);

    public SatelliteRepository()
    {
        LoadPreseededSatellites();
    }

    public void ToggleTracking(int id)
    {
        if (TrackedIds.Contains(id))
            TrackedIds.Remove(id);
        else
            TrackedIds.Add(id);
    }

    public SatelliteEntity? GetById(int id) => Satellites.FirstOrDefault(s => s.Id == id);

    private void LoadPreseededSatellites()
    {
        Satellites = new List<SatelliteEntity>
        {
            new(
                25544,
                "ISS (ZARYA)",
                "stations",
                "1 25544U 98067A   24095.53472222  .00016717  00000-0  10270-3 0  9002",
                "2 25544  51.6416 247.4627 0006703 130.5360 325.0288 15.49887754447413",
                "1998-067A",
                "LEO",
                51.64,
                420.0,
                92.9,
                true,
                Colors[0]
            ),
            new(
                48274,
                "TIANGONG (CSS)",
                "stations",
                "1 48274U 21035A   24095.51234567  .00012450  00000-0  85230-4 0  9991",
                "2 48274  41.4721 180.1234 0004123 220.4501 139.5210 15.61234567167890",
                "2021-035A",
                "LEO",
                41.47,
                388.0,
                92.2,
                true,
                Colors[1]
            ),
            new(
                20580,
                "HUBBLE SPACE TELESCOPE",
                "science",
                "1 20580U 90037B   24095.48712345  .00001240  00000-0  54120-4 0  9994",
                "2 20580  28.4690 120.4512 0002871 280.1245  79.8451 14.98124567845120",
                "1990-037B",
                "LEO",
                28.47,
                535.0,
                95.3,
                true,
                Colors[2]
            ),
            new(
                49260,
                "LANDSAT 9",
                "earth",
                "1 49260U 21088A   24095.45123456  .00000450  00000-0  23410-4 0  9998",
                "2 49260  98.2145  85.4512 0001240 100.1245 260.0124 14.57124567134560",
                "2021-088A",
                "SSO",
                98.21,
                705.0,
                98.8,
                false,
                Colors[3]
            ),
            new(
                25338,
                "NOAA 15",
                "weather",
                "1 25338U 98030A   24095.40123456  .00000120  00000-0  85410-5 0  9993",
                "2 25338  98.7124 110.1245 0011245  75.4512 284.7124 14.25987654345670",
                "1998-030A",
                "SSO",
                98.71,
                807.0,
                101.1,
                false,
                Colors[4]
            ),
            new(
                48859,
                "GPS III-05 (PRN 11)",
                "gps",
                "1 48859U 21054A   24095.35123456  .00000010  00000-0  00000-0 0  9999",
                "2 48859  55.1245  45.1245 0081245 190.1245 169.8451  2.00561234021450",
                "2021-054A",
                "MEO",
                55.12,
                20200.0,
                718.0,
                false,
                Colors[5]
            ),
            new(
                44713,
                "STARLINK-1007",
                "starlink",
                "1 44713U 19074A   24095.61234567  .00004512  00000-0  34120-3 0  9997",
                "2 44713  53.0512 310.1245 0001542  90.4512 269.6541 15.06123456241250",
                "2019-074A",
                "LEO",
                53.05,
                550.0,
                95.6,
                false,
                Colors[6]
            )
        };
    }
}
