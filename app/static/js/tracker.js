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
  params.append('sats', trackedSats.map(s => s.id).join(','));
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

  L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/">CARTO</a>',
    detectRetina: true,
    maxZoom: 19
  }).addTo(map);

  trackedSats.forEach(sat => {
    sat.satrec = satellite.twoline2satrec(sat.line1, sat.line2);
    
    const dot = document.getElementById(`sat-dot-${sat.id}`);
    if (dot) dot.style.background = sat.color;
    const dotTech = document.getElementById(`sat-dot-tech-${sat.id}`);
    if (dotTech) dotTech.style.background = sat.color;

    drawTrack(sat);
  });

  updateSatsFlatMap();
  window._updateFlatTimer = setInterval(updateSatsFlatMap, 2000);
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
    }
  }
};

window.resetMapView = function() {
  if (map) {
    map.setView([20, 0], 2);
  }
};