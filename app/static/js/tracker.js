// ══════════════════════════════════════════════════════════
// Multi-Satellite Tracker — Live orbit map & telemetry
// ══════════════════════════════════════════════════════════

// ========== SIDEBAR TOGGLE ==========
window.toggleSidebarContent = function(headerEl) {
  const content = headerEl.nextElementSibling;
  const icon = headerEl.querySelector('.sidebar-toggle-icon');
  
  if (content.classList.contains('open')) {
    content.classList.remove('open');
    headerEl.classList.remove('open');
    icon.style.transform = 'rotate(0deg)';
  } else {
    content.classList.add('open');
    headerEl.classList.add('open');
    icon.style.transform = 'rotate(-90deg)';
  }
};

// ========== SHARE LINK ==========
window.shareTrackerLink = function() {
  const params = new URLSearchParams();
  params.append('view', 'tracker');
  const satIds = trackedSats.map(s => s.id).join(',');
  params.append('ids', satIds);
  params.append('sats', satIds);
  const url = `${window.location.protocol}//${window.location.host}${window.location.pathname}?${params.toString()}`;
  
  if (navigator.clipboard) {
    navigator.clipboard.writeText(url).then(() => {
      const btn = document.getElementById('share-link-btn');
      const originalText = btn.innerHTML;
      btn.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg> Copied!';
      btn.style.background = 'rgba(16,185,129,0.15)';
      btn.style.borderColor = 'rgba(16,185,129,0.3)';
      btn.style.color = '#6ee7b7';
      setTimeout(() => {
        btn.innerHTML = originalText;
        btn.style.background = '';
        btn.style.borderColor = '';
        btn.style.color = '';
      }, 2000);
    });
  } else {
    const textarea = document.createElement('textarea');
    textarea.value = url;
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand('copy');
    document.body.removeChild(textarea);
    alert('Link copied to clipboard!');
  }
};

// ========== FLAT MAP ==========
const SAT_VIEW_RADIUS_KM = 1000;

function normalizeLng(lng) {
  return ((lng + 180) % 360 + 360) % 360 - 180;
}

function unwrapLongitudes(lngs) {
  const norm = lngs.map(normalizeLng);
  if (norm.length <= 1) return norm;
  const sorted = norm.slice().sort((a, b) => a - b);
  let bestGap = -1;
  let gapAt = 0;
  for (let i = 0; i < sorted.length; i++) {
    const next = i + 1 < sorted.length ? sorted[i + 1] : sorted[0] + 360;
    const gap = next - sorted[i];
    if (gap > bestGap) {
      bestGap = gap;
      gapAt = i;
    }
  }
  const start = sorted[(gapAt + 1) % sorted.length];
  return norm.map((lng) => {
    let x = lng;
    while (x < start) x += 360;
    while (x >= start + 360) x -= 360;
    return x;
  });
}

function currentSatPositions() {
  const now = new Date();
  const points = [];
  trackedSats.forEach((sat) => {
    if (sat.marker) {
      const ll = sat.marker.getLatLng();
      points.push({ lat: ll.lat, lng: ll.lng });
      return;
    }
    if (!sat.satrec) return;
    const posVel = satellite.propagate(sat.satrec, now);
    if (!posVel || !posVel.position) return;
    const gmst = satellite.gstime(now);
    const posGd = satellite.eciToGeodetic(posVel.position, gmst);
    points.push({
      lat: satellite.degreesLat(posGd.latitude),
      lng: satellite.degreesLong(posGd.longitude),
    });
  });
  return points;
}

function boundsForSatelliteCoverage(points, radiusKm) {
  if (!points.length || typeof L === "undefined") return null;
  const lngs = unwrapLongitudes(points.map((p) => p.lng));
  const diameterM = radiusKm * 2 * 1000;
  let bounds = null;
  points.forEach((point, index) => {
    const pad = L.latLng(point.lat, lngs[index]).toBounds(diameterM);
    if (!bounds) {
      bounds = pad;
    } else {
      bounds.extend(pad);
    }
  });
  return bounds;
}

function fitMapToTrackedSats(options) {
  if (!map) return;
  const points = currentSatPositions();
  const bounds = boundsForSatelliteCoverage(points, SAT_VIEW_RADIUS_KM);
  if (!bounds || !bounds.isValid()) return;
  const animate = !options || options.animate !== false;
  map.fitBounds(bounds, {
    padding: [48, 48],
    maxZoom: 8,
    animate: animate,
  });
}

function initFlatMap() {
  if (map) {
    map.remove();
  }

  map = L.map('multi-map', {
    center: [20, 0],
    zoom: 2,
    minZoom: 1,
    maxZoom: 10,
    worldCopyJump: true
  });

  if (window.SatTrackBasemap) {
    SatTrackBasemap.addDefaultBasemap(map);
  }

  trackedSats.forEach(sat => {
    sat.satrec = satellite.twoline2satrec(sat.line1, sat.line2);
    
    const dot = document.getElementById(`sat-dot-${sat.id}`);
    if (dot) dot.style.background = sat.color;
    const dotTech = document.getElementById(`sat-dot-tech-${sat.id}`);
    if (dotTech) dotTech.style.background = sat.color;

    drawTrack(sat);
  });

  updateSatsFlatMap();
  map.whenReady(function() {
    map.invalidateSize();
    fitMapToTrackedSats({ animate: false });
  });
  window._updateFlatTimer = setInterval(updateSatsFlatMap, 2000);
  if (document.getElementById('world-events-overlay')?.checked) {
    toggleWorldEventsOverlay(true);
  }
  if (document.getElementById('markets-overlay')?.checked) {
    toggleMarketsOverlay(true);
  }
  if (document.getElementById('currencies-overlay')?.checked) {
    toggleCurrenciesOverlay(true);
  }
  if (document.getElementById('flights-overlay')?.checked) {
    toggleFlightsOverlay(true);
  }
  if (document.getElementById('news-overlay')?.checked) {
    toggleNewsOverlay(true);
  }
  if (document.getElementById('ships-overlay')?.checked) {
    toggleShipsOverlay(true);
  }
  if (document.getElementById('webcams-overlay')?.checked) {
    toggleWebcamsOverlay(true);
  }
  updateMapDataCredits();
}

let worldEventsLayer = null;
let worldEventsLoaded = false;

function eventMarkerColor(category) {
  const text = (category || '').toLowerCase();
  if (text.includes('earthquake')) return '#f59e0b';
  if (text.includes('wildfire') || text.includes('fire')) return '#ef4444';
  if (text.includes('storm') || text.includes('cyclone')) return '#38bdf8';
  if (text.includes('volcano')) return '#c084fc';
  if (text.includes('flood')) return '#22d3ee';
  return '#eab308';
}

function eventMagnitude(event) {
  if (typeof event.magnitude === 'number' && !Number.isNaN(event.magnitude)) {
    return event.magnitude;
  }
  const match = String(event.category || event.title || '').match(/m\s*([0-9]+(?:\.[0-9]+)?)/i);
  return match ? Number(match[1]) : null;
}

function isEarthquakeEvent(event) {
  if (event.kind === 'earthquake') return true;
  const text = `${event.category || ''} ${event.title || ''} ${event.source || ''}`.toLowerCase();
  return text.includes('earthquake') || text.includes('usgs');
}

function earthquakeMarkerRadius(magnitude) {
  if (magnitude == null || Number.isNaN(Number(magnitude))) return 7;
  return Math.max(5, Math.min(22, 4 + (Number(magnitude) - 4) * 3.5));
}

function earthquakeMarkerColor(magnitude) {
  const mag = Number(magnitude);
  if (Number.isNaN(mag)) return '#f59e0b';
  if (mag >= 7) return '#9f1239';
  if (mag >= 6) return '#ef4444';
  if (mag >= 5.5) return '#f97316';
  if (mag >= 5) return '#fb923c';
  return '#eab308';
}

function escapeHtml(value) {
  return String(value || '').replace(/[&<>"']/g, (ch) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[ch]));
}

function formatEventTime(iso) {
  if (!iso) return 'Last 24 hours';
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toUTCString().replace(' GMT', ' UTC');
}

function formatTempC(value) {
  if (value == null || Number.isNaN(Number(value))) return '—';
  return `${Number(value).toFixed(1)}°C`;
}

function formatTempDelta(value) {
  if (value == null || Number.isNaN(Number(value))) return { text: '—', cls: 'market-popup__flat' };
  const num = Number(value);
  const sign = num > 0 ? '+' : '';
  return {
    text: `${sign}${num.toFixed(1)}°C`,
    cls: num > 0 ? 'market-popup__up' : (num < 0 ? 'market-popup__down' : 'market-popup__flat'),
  };
}

function temperaturePopupHtml(city) {
  const changes = city.changes || {};
  const rows = [
    ['7d', changes['7d']],
    ['30d', changes['30d']],
    ['90d', changes['90d']],
    ['1y', changes['1y']],
  ].map(([label, delta]) => {
    const change = formatTempDelta(delta);
    return `<tr>
      <th>${escapeHtml(label)}</th>
      <td class="temp-popup__pct ${change.cls}">${escapeHtml(change.text)}</td>
    </tr>`;
  }).join('');
  return `
    <div class="temp-popup">
      <strong>${escapeHtml(city.name || 'City')}</strong><br>
      <span style="opacity:0.8">${escapeHtml(city.country || '')} · ${escapeHtml(String(city.pop_m || ''))}M people</span><br>
      Latest ${escapeHtml(formatTempC(city.temp_c))}${city.as_of ? ` · ${escapeHtml(city.as_of)}` : ''}
      <table class="temp-popup__table">
        <tbody>${rows}</tbody>
      </table>
      <div class="overlay-credit">Daily 2 m mean: <a href="https://open-meteo.com/" target="_blank" rel="noopener noreferrer">Open-Meteo</a> (ERA5 / Copernicus). Cities over 1 million people.</div>
    </div>`;
}

function renderWorldEvents(events, temperatures) {
  if (!map) return;
  if (worldEventsLayer) {
    map.removeLayer(worldEventsLayer);
  }
  worldEventsLayer = L.layerGroup();
  (temperatures || []).forEach((city) => {
    if (typeof city.lat !== 'number' || typeof city.lng !== 'number') return;
    const color = city.color || '#94a3b8';
    const icon = L.divIcon({
      className: 'temp-pin-wrap',
      html: `<div class="temp-pin" style="background:${color};border-color:${color}">${escapeHtml(formatTempC(city.temp_c))}</div>`,
      iconSize: [42, 18],
      iconAnchor: [21, 9],
    });
    const marker = L.marker([city.lat, city.lng], { icon: icon, zIndexOffset: 350 });
    const week = formatTempDelta((city.changes || {})['7d']);
    marker.bindTooltip(
      `${escapeHtml(city.name || 'City')} · ${escapeHtml(formatTempC(city.temp_c))} · 7d ${week.text}`,
      { direction: 'top', opacity: 0.95 }
    );
    marker.bindPopup(temperaturePopupHtml(city), { maxWidth: 280, minWidth: 200 });
    worldEventsLayer.addLayer(marker);
  });
  (events || []).forEach((event) => {
    if (typeof event.lat !== 'number' || typeof event.lng !== 'number') return;
    const quake = isEarthquakeEvent(event);
    const magnitude = eventMagnitude(event);
    const color = quake ? earthquakeMarkerColor(magnitude) : eventMarkerColor(event.category);
    const radius = quake ? earthquakeMarkerRadius(magnitude) : 6;
    const marker = L.circleMarker([event.lat, event.lng], {
      radius: radius,
      color: color,
      weight: quake ? 2 : 1,
      fillColor: color,
      fillOpacity: quake ? 0.45 : 0.75,
    });
    const safeUrl = /^https?:\/\//i.test(event.url || '') ? event.url : '';
    const link = safeUrl
      ? `<br><a href="${escapeHtml(safeUrl)}" target="_blank" rel="noopener">Source</a>`
      : '';
    const magLabel = quake && magnitude != null ? `<br>Magnitude ${escapeHtml(Number(magnitude).toFixed(1))}` : '';
    marker.bindPopup(
      `<strong>${escapeHtml(event.title || 'Event')}</strong><br>${escapeHtml(event.category || '')}${magLabel}<br>` +
      `${escapeHtml(formatEventTime(event.time))}<br><span style="opacity:0.8">${escapeHtml(event.source || '')}</span>${link}`
    );
    worldEventsLayer.addLayer(marker);
  });
  worldEventsLayer.addTo(map);
}

window.toggleWorldEventsOverlay = async function(enabled) {
  const box = document.getElementById('world-events-overlay');
  const label = document.getElementById('world-events-toggle');
  if (!enabled) {
    if (worldEventsLayer && map) map.removeLayer(worldEventsLayer);
    if (label) label.title = 'Weather and climate events (NASA EONET), earthquakes (USGS), and temperature trends for cities over 1 million (Open-Meteo).';
    updateMapDataCredits();
    return;
  }
  if (!map) return;
  try {
    if (box) box.disabled = true;
    const res = await fetch('/api/world-events');
    const data = await res.json();
    renderWorldEvents(data.events || [], data.temperatures || []);
    worldEventsLoaded = true;
    const tempCount = (data.temperatures || []).length;
    if (label) label.title = `${data.count || 0} events (24h) · ${tempCount} city temperature trends (7d / 30d / 90d / 1y)`;
    updateMapDataCredits();
  } catch (err) {
    console.error(err);
    alert('Could not load the weather and earthquake overlay.');
    if (box) box.checked = false;
  } finally {
    if (box) box.disabled = false;
  }
};

let marketsLayer = null;

function formatIndexValue(value) {
  if (value == null || Number.isNaN(Number(value))) return '—';
  return Number(value).toLocaleString(undefined, { maximumFractionDigits: 2 });
}

function formatChange(pct) {
  if (pct == null || Number.isNaN(Number(pct))) return { text: '—', cls: 'market-popup__flat' };
  const num = Number(pct);
  const sign = num > 0 ? '+' : '';
  return {
    text: `${sign}${num.toFixed(2)}%`,
    cls: num > 0 ? 'market-popup__up' : (num < 0 ? 'market-popup__down' : 'market-popup__flat'),
  };
}

function marketPopupHtml(market) {
  const changes = market.changes || {};
  const rows = [
    ['1d', changes['1d']],
    ['7d', changes['7d']],
    ['30d', changes['30d']],
    ['1 quarter', changes['1q']],
    ['1 year', changes['1y']],
    ['10 years', changes['10y']],
  ].map(([label, pct]) => {
    const change = formatChange(pct);
    return `<div class="market-popup__change"><span>${escapeHtml(label)}</span><span class="${change.cls}">${change.text}</span></div>`;
  }).join('');
  return `
    <div class="market-popup">
      <strong>#${escapeHtml(market.rank)} ${escapeHtml(market.exchange)}</strong><br>
      <span style="opacity:0.8">${escapeHtml(market.city)} · ~${escapeHtml(market.market_cap_tn)}T USD cap</span><br>
      ${escapeHtml(market.index)} <strong>${formatIndexValue(market.value)}</strong>
      ${rows}
      <div class="overlay-credit">Quotes: <a href="https://www.cnbc.com" target="_blank" rel="noopener noreferrer">CNBC</a> public index levels and 1-day %</div>
    </div>`;
}

function renderMarkets(markets) {
  if (!map) return;
  if (marketsLayer) map.removeLayer(marketsLayer);
  marketsLayer = L.layerGroup();
  (markets || []).forEach((market) => {
    if (typeof market.lat !== 'number' || typeof market.lng !== 'number') return;
    const color = market.color || '#94a3b8';
    const icon = L.divIcon({
      className: 'market-pin-wrap',
      html: `<div class="market-pin" style="background:${color};color:${color}" title="${escapeHtml(market.exchange)}"></div>`,
      iconSize: [18, 18],
      iconAnchor: [9, 9],
    });
    const marker = L.marker([market.lat, market.lng], { icon: icon, zIndexOffset: 400 });
    marker.bindPopup(marketPopupHtml(market));
    marketsLayer.addLayer(marker);
  });
  marketsLayer.addTo(map);
}

window.toggleMarketsOverlay = async function(enabled) {
  const box = document.getElementById('markets-overlay');
  const label = document.getElementById('markets-toggle');
  if (!enabled) {
    if (marketsLayer && map) map.removeLayer(marketsLayer);
    if (label) label.title = 'Major world market indexes. Level and 1-day % from CNBC public quotes.';
    updateMapDataCredits();
    return;
  }
  if (!map) return;
  try {
    if (box) box.disabled = true;
    const res = await fetch('/api/market-indices');
    const data = await res.json();
    renderMarkets(data.markets || []);
    if (label) label.title = `${data.count || 0} market indexes · CNBC 1d`;
    updateMapDataCredits();
  } catch (err) {
    console.error(err);
    alert('Could not load the markets overlay.');
    if (box) box.checked = false;
  } finally {
    if (box) box.disabled = false;
  }
};

let currenciesLayer = null;

const CURRENCY_HORIZONS = [
  ['1d', '1d'],
  ['7d', '7d'],
  ['30d', '30d'],
  ['90d', '90d'],
  ['6m', '6m'],
  ['1y', '1y'],
  ['5y', '5y'],
];

function formatLocalAmount(value) {
  if (value == null || Number.isNaN(Number(value))) return '—';
  const num = Number(value);
  if (Math.abs(num) >= 1000) {
    return num.toLocaleString(undefined, { maximumFractionDigits: 0 });
  }
  if (Math.abs(num) >= 1) {
    return num.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }
  return num.toLocaleString(undefined, { maximumSignificantDigits: 4 });
}

function currencyChangeCells(pcts) {
  return CURRENCY_HORIZONS.map(([key]) => {
    const change = formatChange((pcts || {})[key]);
    return `<td class="currency-popup__pct ${change.cls}">${escapeHtml(change.text)}</td>`;
  }).join('');
}

function currencyPopupHtml(item) {
  const rates = item.rates || {};
  const changes = item.changes || {};
  const baskets = [
    ['USD', '1 USD'],
    ['EUR', '1 EUR'],
    ['JPY', '1 yen'],
    ['XAU', '1 oz gold'],
    ['OIL', '1 barrel oil'],
    ['BIGMAC', '1 Big Mac'],
  ];
  const headerPcts = CURRENCY_HORIZONS.map(([, label]) => `<th>${escapeHtml(label)}</th>`).join('');
  const rows = baskets.map(([code, label]) => {
    const showPct = code !== 'OIL' && code !== 'BIGMAC';
    const pctCells = showPct
      ? currencyChangeCells(changes[code])
      : CURRENCY_HORIZONS.map(() => '<td class="currency-popup__pct market-popup__flat">—</td>').join('');
    return `<tr>
      <th>${escapeHtml(label)}</th>
      <td class="currency-popup__amt">${escapeHtml(formatLocalAmount(rates[code]))}</td>
      ${pctCells}
    </tr>`;
  }).join('');
  return `
    <div class="currency-popup">
      <strong>${escapeHtml(item.code)} · ${escapeHtml(item.name)}</strong><br>
      <span style="opacity:0.8">${escapeHtml(item.city || '')} · how many ${escapeHtml(item.code)} to buy</span>
      <table class="currency-popup__table">
        <thead><tr><th></th><th></th>${headerPcts}</tr></thead>
        <tbody>${rows}</tbody>
      </table>
      <div class="overlay-credit">
        FX &amp; gold: <a href="https://frankfurter.dev" target="_blank" rel="noopener noreferrer">Frankfurter</a>
        · oil: <a href="https://www.cnbc.com/quotes/@CL.1" target="_blank" rel="noopener noreferrer">CNBC WTI</a>
        · burger: <a href="https://github.com/TheEconomist/big-mac-data" target="_blank" rel="noopener noreferrer">The Economist Big Mac Index</a>
      </div>
    </div>`;
}

function renderCurrencies(currencies) {
  if (!map) return;
  if (currenciesLayer) map.removeLayer(currenciesLayer);
  currenciesLayer = L.layerGroup();
  (currencies || []).forEach((item) => {
    if (typeof item.lat !== 'number' || typeof item.lng !== 'number') return;
    const color = item.color || '#94a3b8';
    const icon = L.divIcon({
      className: 'currency-pin-wrap',
      html: `<div class="currency-pin" style="background:${color};border-color:${color}">${escapeHtml(item.code || '')}</div>`,
      iconSize: [34, 18],
      iconAnchor: [17, 9],
    });
    const marker = L.marker([item.lat, item.lng], { icon: icon, zIndexOffset: 390 });
    const perUsd = formatLocalAmount(item.rates && item.rates.USD);
    marker.bindTooltip(
      `${escapeHtml(item.code || '')} · ${escapeHtml(perUsd)} per $1`,
      { direction: 'top', opacity: 0.95 }
    );
    marker.bindPopup(currencyPopupHtml(item), { maxWidth: 560, minWidth: 420 });
    currenciesLayer.addLayer(marker);
  });
  currenciesLayer.addTo(map);
}

window.toggleCurrenciesOverlay = async function(enabled) {
  const box = document.getElementById('currencies-overlay');
  const label = document.getElementById('currencies-toggle');
  if (!enabled) {
    if (currenciesLayer && map) map.removeLayer(currenciesLayer);
    if (label) label.title = 'Local units needed to buy 1 USD, 1 EUR, 1 yen, 1 oz gold, 1 barrel of oil, and 1 Big Mac.';
    updateMapDataCredits();
    return;
  }
  if (!map) return;
  try {
    if (box) box.disabled = true;
    const res = await fetch('/api/currencies');
    const data = await res.json();
    renderCurrencies(data.currencies || []);
    if (label) label.title = `${data.count || 0} currencies · Frankfurter / CNBC / Big Mac Index`;
    updateMapDataCredits();
  } catch (err) {
    console.error(err);
    alert('Could not load the currencies overlay.');
    if (box) box.checked = false;
  } finally {
    if (box) box.disabled = false;
  }
};

let flightsLayer = null;
let flightsTimer = null;
let flightsMoveHandler = null;

function flightColor(flight) {
  const alt = flight.altitude_m;
  if (alt == null) return '#38bdf8';
  if (alt < 3000) return '#38bdf8';
  if (alt < 10000) return '#34d399';
  return '#c4b5fd';
}

function flightPopupHtml(flight) {
  const callsign = flight.callsign || flight.icao24 || 'Aircraft';
  const altFt = flight.altitude_m == null ? '—' : `${Math.round(flight.altitude_m * 3.28084).toLocaleString()} ft`;
  const speed = flight.velocity_ms == null ? '—' : `${Math.round(flight.velocity_ms * 3.6)} km/h`;
  const heading = flight.heading == null ? '—' : `${Math.round(flight.heading)}°`;
  const origin = flight.origin_label || 'Unknown origin';
  const destination = flight.destination_label || 'Unknown destination';
  const status = flight.status_label || 'Timing unknown';
  const delay = flight.delay_minutes ? ` · ${escapeHtml(String(flight.delay_minutes))} min` : '';
  return `
    <div class="flight-popup">
      <strong>${escapeHtml(callsign)}</strong><br>
      <span style="opacity:0.8">${escapeHtml(flight.origin_country || '')}</span><br>
      Origin ${escapeHtml(origin)}<br>
      Destination ${escapeHtml(destination)}<br>
      ${escapeHtml(status)}${delay}<br>
      Alt ${escapeHtml(altFt)} · ${escapeHtml(speed)} · Hdg ${escapeHtml(heading)}
      <div class="overlay-credit">ADS-B: <a href="https://opensky-network.org" target="_blank" rel="noopener noreferrer">OpenSky Network</a> · route: <a href="https://www.adsbdb.com" target="_blank" rel="noopener noreferrer">adsbdb</a>. On-time is estimated, not an airline schedule.</div>
    </div>`;
}

function renderFlights(flights) {
  if (!map) return;
  if (flightsLayer) map.removeLayer(flightsLayer);
  flightsLayer = L.layerGroup();
  (flights || []).forEach((flight) => {
    if (typeof flight.lat !== 'number' || typeof flight.lng !== 'number') return;
    const color = flightColor(flight);
    const heading = typeof flight.heading === 'number' ? flight.heading : 0;
    const icon = L.divIcon({
      className: 'flight-pin-wrap',
      html: `<div class="flight-pin" style="color:${color};transform:rotate(${heading}deg)">
        <svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M21 16v-2l-8-5V3.5a1.5 1.5 0 0 0-3 0V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5l8 2.5z"/></svg>
      </div>`,
      iconSize: [18, 18],
      iconAnchor: [9, 9],
    });
    const marker = L.marker([flight.lat, flight.lng], { icon: icon, zIndexOffset: 300 });
    const routeHint = [flight.origin_label, flight.destination_label].filter(Boolean).join(' → ') || flight.origin_country || 'Aircraft';
    const statusHint = flight.status_label ? ` · ${flight.status_label}` : '';
    marker.bindTooltip(`${escapeHtml(flight.callsign || flight.icao24 || 'Aircraft')} · ${escapeHtml(routeHint)}${escapeHtml(statusHint)}`, { direction: 'top', opacity: 0.95 });
    marker.bindPopup(flightPopupHtml(flight));
    flightsLayer.addLayer(marker);
  });
  flightsLayer.addTo(map);
}

function currentFlightQuery() {
  if (!map) return '';
  const bounds = map.getBounds();
  const params = new URLSearchParams({
    lamin: Math.max(-90, bounds.getSouth()).toFixed(2),
    lomin: Math.max(-180, Math.min(180, bounds.getWest())).toFixed(2),
    lamax: Math.min(90, bounds.getNorth()).toFixed(2),
    lomax: Math.max(-180, Math.min(180, bounds.getEast())).toFixed(2),
  });
  return params.toString();
}

async function refreshFlightsOverlay() {
  const box = document.getElementById('flights-overlay');
  const label = document.getElementById('flights-toggle');
  if (!box?.checked || !map) return;
  const query = currentFlightQuery();
  const res = await fetch(`/api/flights${query ? `?${query}` : ''}`);
  const data = await res.json();
  renderFlights(data.flights || []);
  if (label) label.title = `${data.count || 0} airborne · OpenSky Network`;
  updateMapDataCredits();
}

window.toggleFlightsOverlay = async function(enabled) {
  const box = document.getElementById('flights-overlay');
  const label = document.getElementById('flights-toggle');
  if (flightsTimer) {
    clearInterval(flightsTimer);
    flightsTimer = null;
  }
  if (flightsMoveHandler && map) {
    map.off('moveend', flightsMoveHandler);
    flightsMoveHandler = null;
  }
  if (!enabled) {
    if (flightsLayer && map) map.removeLayer(flightsLayer);
    if (label) label.title = 'Live aircraft from The OpenSky Network';
    updateMapDataCredits();
    return;
  }
  if (!map) return;
  try {
    if (box) box.disabled = true;
    await refreshFlightsOverlay();
    flightsTimer = setInterval(() => {
      refreshFlightsOverlay().catch((err) => console.error(err));
    }, 20000);
    let moveTimer = null;
    flightsMoveHandler = function() {
      clearTimeout(moveTimer);
      moveTimer = setTimeout(() => {
        refreshFlightsOverlay().catch((err) => console.error(err));
      }, 800);
    };
    map.on('moveend', flightsMoveHandler);
  } catch (err) {
    console.error(err);
    alert('Could not load the flights overlay.');
    if (box) box.checked = false;
  } finally {
    if (box) box.disabled = false;
  }
};

let newsLayer = null;

function newsPopupHtml(item) {
  const links = (item.articles && item.articles.length ? item.articles : [{ title: item.title, url: item.url }])
    .filter((article) => /^https?:\/\//i.test(article.url || ''))
    .map((article) => (
      `<a class="news-popup__link" href="${escapeHtml(article.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(article.title || 'Open article')}</a>`
    ))
    .join('');
  return `
    <div class="news-popup">
      ${links || escapeHtml(item.title || 'News')}
      <div class="overlay-credit">${escapeHtml(item.region || '')} · ${escapeHtml(item.source || 'News')} · <a href="https://www.gdacs.org" target="_blank" rel="noopener noreferrer">GDACS</a> / <a href="https://en.wikipedia.org" target="_blank" rel="noopener noreferrer">Wikipedia</a></div>
    </div>`;
}

function renderNews(items) {
  if (!map) return;
  if (newsLayer) map.removeLayer(newsLayer);
  newsLayer = L.layerGroup();
  (items || []).forEach((item) => {
    if (typeof item.lat !== 'number' || typeof item.lng !== 'number') return;
    const marker = L.circleMarker([item.lat, item.lng], {
      radius: 7,
      color: '#f472b6',
      weight: 1,
      fillColor: '#fb7185',
      fillOpacity: 0.8,
    });
    marker.bindTooltip(escapeHtml(item.title || item.region || 'News'), { direction: 'top', opacity: 0.95 });
    marker.bindPopup(newsPopupHtml(item));
    newsLayer.addLayer(marker);
  });
  newsLayer.addTo(map);
}

window.toggleNewsOverlay = async function(enabled) {
  const box = document.getElementById('news-overlay');
  const label = document.getElementById('news-toggle');
  if (!enabled) {
    if (newsLayer && map) map.removeLayer(newsLayer);
    if (label) label.title = 'Geo-tagged alerts from GDACS and Wikipedia featured news.';
    updateMapDataCredits();
    return;
  }
  if (!map) return;
  try {
    if (box) box.disabled = true;
    const res = await fetch('/api/geo-news');
    const data = await res.json();
    renderNews(data.news || []);
    if (label) label.title = `${data.count || 0} stories · GDACS / Wikipedia`;
    updateMapDataCredits();
  } catch (err) {
    console.error(err);
    alert('Could not load the news overlay.');
    if (box) box.checked = false;
  } finally {
    if (box) box.disabled = false;
  }
};

let shipsLayer = null;
let shipsTimer = null;

function shipColor(shipClass) {
  if (shipClass === 'tanker') return '#f59e0b';
  if (shipClass === 'passenger') return '#38bdf8';
  if (shipClass === 'cargo') return '#22d3ee';
  if (shipClass === 'fishing') return '#a3e635';
  return '#94a3b8';
}

function formatShipCoord(lat, lng) {
  if (typeof lat !== 'number' || typeof lng !== 'number') return 'Location unknown';
  const ns = lat >= 0 ? 'N' : 'S';
  const ew = lng >= 0 ? 'E' : 'W';
  return `${Math.abs(lat).toFixed(4)}°${ns}, ${Math.abs(lng).toFixed(4)}°${ew}`;
}

function shipLocationText(ship) {
  const when = ship.time ? formatEventTime(ship.time) : 'Latest AIS report';
  return `${formatShipCoord(ship.lat, ship.lng)}<br>${escapeHtml(when)}`;
}

function shipPopupHtml(ship) {
  const srcUrl = /^https?:\/\//i.test(ship.source_url || '') ? ship.source_url : 'https://www.digitraffic.fi/en/marine-traffic/';
  return `
    <div class="ship-popup">
      <strong>${escapeHtml(ship.name || 'Vessel')}</strong><br>
      ${shipLocationText(ship)}
      <div class="overlay-credit">Current AIS position: <a href="${escapeHtml(srcUrl)}" target="_blank" rel="noopener noreferrer">${escapeHtml(ship.source || 'Fintraffic Digitraffic')}</a> (CC BY 4.0)</div>
    </div>`;
}

function shipIcon(ship) {
  const color = shipColor(ship.ship_class);
  return L.divIcon({
    className: 'ship-pin-wrap',
    html: `<div class="ship-pin" style="color:${color}">
      <svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M4 14 12 3l8 11-2 6H6l-2-6zm8-7.2L7.4 13h9.2L12 6.8z"/></svg>
    </div>`,
    iconSize: [16, 16],
    iconAnchor: [8, 8],
  });
}

function renderShipping(data) {
  if (!map) return;
  if (shipsLayer) map.removeLayer(shipsLayer);
  shipsLayer = L.layerGroup();
  (data.ships || []).forEach((ship) => {
    if (typeof ship.lat !== 'number' || typeof ship.lng !== 'number') return;
    const marker = L.marker([ship.lat, ship.lng], { icon: shipIcon(ship), zIndexOffset: 280 });
    marker.bindTooltip(
      `<div class="ship-tooltip"><strong>${escapeHtml(ship.name || 'Vessel')}</strong><br>${shipLocationText(ship)}</div>`,
      { direction: 'top', opacity: 0.95, className: 'ship-tooltip-wrap' }
    );
    marker.bindPopup(shipPopupHtml(ship));
    shipsLayer.addLayer(marker);
  });
  shipsLayer.addTo(map);
}

async function refreshShipsOverlay() {
  const box = document.getElementById('ships-overlay');
  const label = document.getElementById('ships-toggle');
  if (!box?.checked || !map) return;
  const res = await fetch('/api/shipping');
  const data = await res.json();
  renderShipping(data);
  if (label) label.title = `${data.ship_count || 0} current AIS positions (Digitraffic, CC BY 4.0)`;
  updateMapDataCredits();
}

window.toggleShipsOverlay = async function(enabled) {
  const box = document.getElementById('ships-overlay');
  const label = document.getElementById('ships-toggle');
  if (shipsTimer) {
    clearInterval(shipsTimer);
    shipsTimer = null;
  }
  if (!enabled) {
    if (shipsLayer && map) map.removeLayer(shipsLayer);
    if (label) label.title = 'Current AIS positions from Fintraffic Digitraffic (CC BY 4.0). Hover a vessel for its latest location.';
    updateMapDataCredits();
    return;
  }
  if (!map) return;
  try {
    if (box) box.disabled = true;
    await refreshShipsOverlay();
    shipsTimer = setInterval(() => {
      refreshShipsOverlay().catch((err) => console.error(err));
    }, 15000);
  } catch (err) {
    console.error(err);
    alert('Could not load current AIS positions from Digitraffic.');
    if (box) box.checked = false;
  } finally {
    if (box) box.disabled = false;
  }
};

let webcamsLayer = null;
let webcamsMoveHandler = null;

function webcamPopupHtml(cam) {
  const url = /^https?:\/\//i.test(cam.url || '') ? cam.url : '';
  const title = cam.name || 'Public webcam';
  const link = url
    ? `<a class="webcam-popup__link" href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(title)}</a>`
    : `<strong>${escapeHtml(title)}</strong>`;
  return `
    <div class="webcam-popup">
      ${link}
      <div class="overlay-credit">${escapeHtml(cam.city || '')} · ${escapeHtml(cam.source || 'Public webcam')}</div>
    </div>`;
}

function renderWebcams(cams) {
  if (!map) return;
  if (webcamsLayer) map.removeLayer(webcamsLayer);
  webcamsLayer = L.layerGroup();
  (cams || []).forEach((cam) => {
    if (typeof cam.lat !== 'number' || typeof cam.lng !== 'number') return;
    const marker = L.circleMarker([cam.lat, cam.lng], {
      radius: 7,
      color: '#67e8f9',
      weight: 1,
      fillColor: '#22d3ee',
      fillOpacity: 0.85,
    });
    marker.bindTooltip(escapeHtml(cam.name || 'Webcam'), { direction: 'top', opacity: 0.95 });
    marker.bindPopup(webcamPopupHtml(cam));
    webcamsLayer.addLayer(marker);
  });
  webcamsLayer.addTo(map);
}

async function refreshWebcamsOverlay() {
  const box = document.getElementById('webcams-overlay');
  const label = document.getElementById('webcams-toggle');
  if (!box?.checked || !map) return;
  const query = currentFlightQuery();
  const res = await fetch(`/api/webcams${query ? `?${query}` : ''}`);
  const data = await res.json();
  renderWebcams(data.webcams || []);
    if (label) label.title = `${data.count || 0} public webcams · official pages / OpenStreetMap`;
  updateMapDataCredits();
}

window.toggleWebcamsOverlay = async function(enabled) {
  const box = document.getElementById('webcams-overlay');
  const label = document.getElementById('webcams-toggle');
  if (webcamsMoveHandler && map) {
    map.off('moveend', webcamsMoveHandler);
    webcamsMoveHandler = null;
  }
  if (!enabled) {
    if (webcamsLayer && map) map.removeLayer(webcamsLayer);
    if (label) label.title = 'Public webcam pages worldwide. Official indexes plus OpenStreetMap. Click a pin to open the feed.';
    updateMapDataCredits();
    return;
  }
  if (!map) return;
  try {
    if (box) box.disabled = true;
    await refreshWebcamsOverlay();
    let moveTimer = null;
    webcamsMoveHandler = function() {
      clearTimeout(moveTimer);
      moveTimer = setTimeout(() => {
        refreshWebcamsOverlay().catch((err) => console.error(err));
      }, 900);
    };
    map.on('moveend', webcamsMoveHandler);
  } catch (err) {
    console.error(err);
    alert('Could not load the webcams overlay.');
    if (box) box.checked = false;
  } finally {
    if (box) box.disabled = false;
  }
};

function updateMapDataCredits() {
  const el = document.getElementById('map-data-credits');
  if (!el) return;
  const parts = ['Basemap: Esri, HERE, Garmin, FAO, NOAA, USGS'];
  if (document.getElementById('world-events-overlay')?.checked) {
    parts.push('Weather & climate: NASA EONET · Earthquakes: USGS · City temps: Open-Meteo ERA5 (7d / 30d / 90d / 1y)');
  }
  if (document.getElementById('markets-overlay')?.checked) {
    parts.push('Index quotes: CNBC (level + 1d %)');
  }
  if (document.getElementById('currencies-overlay')?.checked) {
    parts.push('FX & gold: Frankfurter · oil: CNBC WTI · burger: The Economist Big Mac Index');
  }
  if (document.getElementById('flights-overlay')?.checked) {
    parts.push('Aircraft: OpenSky Network');
  }
  if (document.getElementById('news-overlay')?.checked) {
    parts.push('News: GDACS disaster alerts · Wikipedia featured stories');
  }
  if (document.getElementById('ships-overlay')?.checked) {
    parts.push('Current AIS positions: Fintraffic Digitraffic (CC BY 4.0, Finland/Baltic)');
  }
  if (document.getElementById('webcams-overlay')?.checked) {
    parts.push('Webcams: USGS, NPS, NOAA, INGV, GeoNet and other official pages · extra pins © OpenStreetMap contributors (ODbL)');
  }
  el.textContent = parts.join(' · ');
}

function drawTrack(sat) {
  if (!sat.satrec) return;
  
  sat.trackLines.forEach(l => map.removeLayer(l));
  sat.trackLines = [];

  if (!sat.showTrack) return;

  const periodMin = 1440 / sat.meanMotion;
  const points = [];
  const start = new Date();

  for (let i = 0; i <= periodMin + 1; i += 1.5) {
    const time = new Date(start.getTime() + i * 60 * 1000);
    const posVel = satellite.propagate(sat.satrec, time);
    const gmst = satellite.gstime(time);
    if (posVel && posVel.position) {
      const posGd = satellite.eciToGeodetic(posVel.position, gmst);
      points.push({
        lat: satellite.degreesLat(posGd.latitude),
        lng: satellite.degreesLong(posGd.longitude)
      });
    }
  }

  let currentSegment = [];
  const paths = [currentSegment];
  for (let i = 0; i < points.length; i++) {
    const pt = points[i];
    if (i > 0) {
      const prev = points[i - 1];
      if (Math.abs(pt.lng - prev.lng) > 180) {
        currentSegment = [];
        paths.push(currentSegment);
      }
    }
    currentSegment.push([pt.lat, pt.lng]);
  }

  paths.forEach(segment => {
    if (segment.length > 0) {
      const poly = L.polyline(segment, {
        color: sat.color,
        weight: 2.5,
        opacity: 0.85,
        dashArray: '5, 3'
      }).addTo(map);
      sat.trackLines.push(poly);
    }
  });
}

function updateSatsFlatMap() {
  const now = new Date();
  trackedSats.forEach(sat => {
    if (!sat.satrec) return;
    const posVel = satellite.propagate(sat.satrec, now);
    const gmst = satellite.gstime(now);

    if (posVel && posVel.position) {
      const posGd = satellite.eciToGeodetic(posVel.position, gmst);
      const lat = satellite.degreesLat(posGd.latitude);
      const lng = satellite.degreesLong(posGd.longitude);
      const alt = posGd.height;
      
      const vel = posVel.velocity;
      const speedKms = Math.sqrt(vel.x * vel.x + vel.y * vel.y + vel.z * vel.z);
      const speedKmh = speedKms * 3600;

      const card = document.getElementById(`sat-card-${sat.id}`);
      if (card) {
        card.querySelector('.live-lat').textContent = lat.toFixed(4) + '°';
        card.querySelector('.live-lng').textContent = lng.toFixed(4) + '°';
        card.querySelector('.live-alt').textContent = alt.toFixed(1) + ' km';
        card.querySelector('.live-vel').textContent = speedKmh.toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ",") + ' km/h';
      }

      const latlng = [lat, lng];
      if (!sat.marker) {
        const satIcon = L.divIcon({
          className: `sat-icon-marker-${sat.id}`,
          html: `<div style="font-size: 24px; line-height: 1; margin-left: -12px; margin-top: -12px; filter: drop-shadow(0 0 5px ${sat.color}); animation: pulse 2s infinite;">🛰️</div>`,
          iconSize: [24, 24]
        });
        sat.marker = L.marker(latlng, {icon: satIcon}).addTo(map);
        sat.marker.bindPopup(`<strong>${sat.name}</strong><br>NORAD: ${sat.id}<br>Alt: ${alt.toFixed(1)} km`);
      } else {
        sat.marker.setLatLng(latlng);
      }
    }
  });
}

// ========== GENERAL FUNCTIONS ==========
window.toggleTrack = function(id, visible) {
  const sat = trackedSats.find(s => s.id === id);
  if (sat) {
    sat.showTrack = visible;
    if (map) {
      drawTrack(sat);
    }
  }
  // Show/hide the global paths toggle button based on whether any track is visible
  const anyVisible = trackedSats.some(s => s.showTrack);
  const btn = document.getElementById('toggle-paths-btn');
  if (btn) {
    btn.style.display = anyVisible ? '' : 'none';
  }
};

window.toggleAllPaths = function() {
  const btn = document.getElementById('toggle-paths-btn');
  const allVisible = btn.textContent.trim() === '🛤️ Paths Off';

  trackedSats.forEach(sat => {
    if (sat.showTrack === allVisible) {
      sat.showTrack = !allVisible;
      const card = document.getElementById(`sat-card-${sat.id}`);
      if (card) {
        const cb = card.querySelector('.toggle-label input[type="checkbox"]');
        if (cb) cb.checked = !allVisible;
      }
    }
    if (map) drawTrack(sat);
  });

  btn.textContent = allVisible ? '🛤️ Paths On' : '🛤️ Paths Off';
};

window.removeSat = function(id) {
  const index = trackedSats.findIndex(s => s.id === id);
  if (index !== -1) {
    const sat = trackedSats[index];
    
    if (map) {
      if (sat.marker) map.removeLayer(sat.marker);
      sat.trackLines.forEach(l => map.removeLayer(l));
    }

    const card = document.getElementById(`sat-card-${id}`);
    if (card) card.remove();
    const techCard = document.getElementById(`sat-tech-${id}`);
    if (techCard) techCard.remove();

    trackedSats.splice(index, 1);

    if (trackedSats.length === 0) {
      document.getElementById('tracker-empty-state').style.display = 'block';
      document.getElementById('tracker-grid-container').style.display = 'none';
    } else {
      fitMapToTrackedSats({ animate: true });
    }
  }
};

window.resetMapView = function() {
  fitMapToTrackedSats({ animate: true });
};

window.toggleTrackerMapFullscreen = function() {
  const shell = document.getElementById('tracker-map-shell');
  const btn = document.getElementById('tracker-fullscreen-btn');
  if (!shell || !btn) return;
  const on = shell.classList.toggle('is-fullscreen');
  document.body.classList.toggle('map-fullscreen-open', on);
  btn.textContent = on ? 'Exit full screen' : 'Full screen';
  btn.setAttribute('aria-pressed', on ? 'true' : 'false');
  btn.title = on ? 'Return map to page' : 'Open map full screen';
  setTimeout(function() {
    if (!map) return;
    map.invalidateSize();
    fitMapToTrackedSats({ animate: false });
  }, 80);
};

document.addEventListener('keydown', function(event) {
  if (event.key !== 'Escape') return;
  const shell = document.getElementById('tracker-map-shell');
  if (shell && shell.classList.contains('is-fullscreen')) {
    window.toggleTrackerMapFullscreen();
  }
});