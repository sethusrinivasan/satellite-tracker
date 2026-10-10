/**
 * Leaflet basemap with no required API key.
 *
 * CARTO dark_all tiles now watermark "API KEY REQUIRED" unless ?key= is set.
 * Default is Esri World Dark Gray (free for reasonable non-commercial use).
 *
 * Optional: set window.SATTRACK_CARTO_KEY (from CARTO_API_KEY env) to keep CARTO.
 */
(function (root) {
  const CARTO_ATTR =
    '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>';
  const ESRI_ATTR =
    'Tiles &copy; Esri &mdash; Esri, HERE, Garmin, FAO, NOAA, USGS';
  const OSM_ATTR =
    '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';

  function cartoKey() {
    return (root.SATTRACK_CARTO_KEY || "").trim();
  }

  function addDefaultBasemap(map) {
    const key = cartoKey();
    if (key && typeof L !== "undefined") {
      L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png?key=" + encodeURIComponent(key), {
        attribution: CARTO_ATTR,
        subdomains: "abcd",
        maxZoom: 19,
        detectRetina: true,
      }).addTo(map);
      return;
    }

    L.tileLayer(
      "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}",
      { attribution: ESRI_ATTR, maxZoom: 16 }
    ).addTo(map);
    L.tileLayer(
      "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Reference/MapServer/tile/{z}/{y}/{x}",
      { attribution: "", maxZoom: 16, pane: "overlayPane" }
    ).addTo(map);
  }

  root.SatTrackBasemap = {
    addDefaultBasemap: addDefaultBasemap,
    attributions: { CARTO_ATTR: CARTO_ATTR, ESRI_ATTR: ESRI_ATTR, OSM_ATTR: OSM_ATTR },
  };
})(window);
