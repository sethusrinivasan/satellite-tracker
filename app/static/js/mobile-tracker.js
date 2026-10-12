/**
 * Satellite TLE Tracker — Core Mobile Application Controller
 * Handles 2D Leaflet tracking, 3D WebGL globe, pass predictor,
 * and offline/remote AI orbital discovery.
 */

(function (root) {
  'use strict';

  const EARTH_RADIUS_KM = 6378.137;
  const COLORS = ['#38bdf8', '#10b981', '#f59e0b', '#a855f7', '#ec4899', '#06b6d4', '#eab308'];

  class MobileTrackerApp {
    constructor() {
      this.trackedSatIds = [25544, 48274, 20580]; // Default: ISS, Tiangong, Hubble
      this.activeSatId = 25544; // Selected satellite for telemetry
      this.activeTab = 'track';
      
      // Observer location (Default: 37.7749° N, 122.4194° W)
      this.observer = {
        lat: 37.7749,
        lng: -122.4194,
        altKm: 0.03,
        name: "Observer (Default)"
      };

      // Map & 3D Globe state
      this.map = null;
      this.satMarkers = {};
      this.satTracks = {};
      this.satFootprints = {};
      this.terminatorLayer = null;
      this.observerMarker = null;

      // 3D Scene
      this.scene3d = null;
      this.camera3d = null;
      this.renderer3d = null;
      this.earth3d = null;
      this.satMeshes3d = {};
      this.orbitRings3d = {};
      this.isGlobeRotating = false;

      // Telemetry update timer
      this.updateTimer = null;
      this.updateIntervalMs = 2000;
    }

    init() {
      this.loadSettings();
      this.setupNavigation();
      this.setupSearch();
      this.setupPasses();
      this.setupAI();
      this.setupBackButton();
      this.requestObserverLocation();

      // Initialize 2D Map on Track tab
      this.init2DMap();

      // Start periodic SGP4 orbital propagation
      this.startOrbitalUpdates();

      // Render initial catalog
      this.renderCatalogList();
      this.updateSyncInfo();
    }

    // ============================================================
    // Navigation & Tabs
    // ============================================================
    setupNavigation() {
      const navItems = document.querySelectorAll('.nav-item');
      navItems.forEach(btn => {
        btn.addEventListener('click', () => {
          const tab = btn.getAttribute('data-tab');
          this.switchTab(tab);
        });
      });

      // Bottom sheet drag handle
      const handle = document.getElementById('sheet-handle-row');
      const sheet = document.getElementById('telemetry-sheet');
      if (handle && sheet) {
        handle.addEventListener('click', () => {
          sheet.classList.toggle('expanded');
        });
      }
    }

    switchTab(tabId) {
      if (this.activeTab === tabId) return;
      this.activeTab = tabId;

      document.querySelectorAll('.nav-item').forEach(btn => {
        btn.classList.toggle('active', btn.getAttribute('data-tab') === tabId);
      });

      document.querySelectorAll('.tab-view').forEach(view => {
        view.classList.toggle('active', view.id === `tab-${tabId}`);
      });

      // Adjust views
      if (tabId === 'track') {
        if (this.map) {
          setTimeout(() => this.map.invalidateSize(), 150);
        }
      } else if (tabId === 'globe') {
        if (!this.renderer3d) {
          this.init3DGlobe();
        } else {
          setTimeout(() => this.resize3D(), 150);
        }
      } else if (tabId === 'passes') {
        this.computeAndRenderPasses();
      }
    }

    setupBackButton() {
      window.history.pushState({ app: 'sattrack' }, '');
      window.addEventListener('popstate', (e) => {
        const modal = document.querySelector('.modal-overlay.active');
        const sheet = document.getElementById('telemetry-sheet');
        if (modal) {
          modal.classList.remove('active');
          window.history.pushState({ app: 'sattrack' }, '');
          return;
        }
        if (sheet && sheet.classList.contains('expanded')) {
          sheet.classList.remove('expanded');
          window.history.pushState({ app: 'sattrack' }, '');
          return;
        }
        if (this.activeTab !== 'track') {
          this.switchTab('track');
          window.history.pushState({ app: 'sattrack' }, '');
        }
      });
    }

    // ============================================================
    // SGP4 Orbital Propagation Engine
    // ============================================================
    propagateSatellite(sat, date = new Date()) {
      if (!window.satellite || !sat.line1 || !sat.line2) return null;
      if (!sat.satrec) {
        sat.satrec = window.satellite.twoline2satrec(sat.line1, sat.line2);
      }

      const posVel = window.satellite.propagate(sat.satrec, date);
      if (!posVel || !posVel.position || !posVel.velocity) return null;

      const gmst = window.satellite.gstime(date);
      const posGd = window.satellite.eciToGeodetic(posVel.position, gmst);

      const latDeg = (posGd.latitude * 180) / Math.PI;
      const lngDeg = ((posGd.longitude * 180) / Math.PI + 180) % 360 - 180;
      const altKm = posGd.height;

      const vx = posVel.velocity.x;
      const vy = posVel.velocity.y;
      const vz = posVel.velocity.z;
      const velKmS = Math.sqrt(vx * vx + vy * vy + vz * vz);
      const velMph = velKmS * 2236.936;

      // Visibility footprint radius (geometric horizon distance)
      const footprintAngle = Math.acos(Math.min(1.0, EARTH_RADIUS_KM / (EARTH_RADIUS_KM + altKm)));
      const footprintRadiusKm = EARTH_RADIUS_KM * footprintAngle;

      return {
        lat: latDeg,
        lng: lngDeg,
        altKm: Math.round(altKm * 10) / 10,
        velKmS: Math.round(velKmS * 100) / 100,
        velMph: Math.round(velMph),
        footprintKm: Math.round(footprintRadiusKm),
        date
      };
    }

    computeGroundTrack(sat, minutes = 90, stepMinutes = 2) {
      if (!window.satellite || !sat.line1 || !sat.line2) return [];
      if (!sat.satrec) {
        sat.satrec = window.satellite.twoline2satrec(sat.line1, sat.line2);
      }

      const now = new Date();
      const segments = [[]];
      let lastLng = null;

      for (let i = -10; i <= minutes; i += stepMinutes) {
        const t = new Date(now.getTime() + i * 60000);
        const posVel = window.satellite.propagate(sat.satrec, t);
        if (!posVel || !posVel.position) continue;

        const gmst = window.satellite.gstime(t);
        const posGd = window.satellite.eciToGeodetic(posVel.position, gmst);
        const lat = (posGd.latitude * 180) / Math.PI;
        const lng = ((posGd.longitude * 180) / Math.PI + 180) % 360 - 180;

        if (lastLng !== null && Math.abs(lng - lastLng) > 180) {
          segments.push([]);
        }
        segments[segments.length - 1].push([lat, lng]);
        lastLng = lng;
      }

      return segments.filter(seg => seg.length > 1);
    }

    startOrbitalUpdates() {
      this.updateTelemetry();
      this.updateTimer = setInterval(() => {
        this.updateTelemetry();
      }, this.updateIntervalMs);
    }

    updateTelemetry() {
      const now = new Date();
      const trackedSats = this.trackedSatIds
        .map(id => root.MobileSatelliteCatalog.getById(id))
        .filter(Boolean);

      trackedSats.forEach((sat, idx) => {
        const color = COLORS[idx % COLORS.length];
        const state = this.propagateSatellite(sat, now);
        if (!state) return;

        // 2D Map Marker & Tracks
        if (this.map) {
          this.update2DMapMarker(sat, state, color);
        }

        // 3D Globe Mesh
        if (this.scene3d) {
          this.update3DObject(sat, state, color);
        }

        // Active satellite telemetry HUD
        if (sat.id === this.activeSatId) {
          this.renderHUD(sat, state, color);
        }
      });

      // Update solar terminator on 2D map
      if (this.map) {
        this.updateSolarTerminator(now);
      }
    }

    // ============================================================
    // 2D Leaflet Map
    // ============================================================
    init2DMap() {
      const mapContainer = document.getElementById('mobile-map');
      if (!mapContainer || typeof L === 'undefined') return;

      this.map = L.map('mobile-map', {
        center: [20, 0],
        zoom: 2,
        minZoom: 1,
        maxZoom: 9,
        zoomControl: false,
        attributionControl: false
      });

      // Dark canvas tiles (Carto / Esri Dark Canvas)
      L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}', {
        maxZoom: 16
      }).addTo(this.map);

      // Add observer location marker
      this.updateObserverMapMarker();

      // Center map button
      document.getElementById('btn-center-map')?.addEventListener('click', () => {
        const activeSat = root.MobileSatelliteCatalog.getById(this.activeSatId);
        if (activeSat) {
          const state = this.propagateSatellite(activeSat);
          if (state) this.map.setView([state.lat, state.lng], 3);
        }
      });
    }

    update2DMapMarker(sat, state, color) {
      const id = sat.id;
      const latlng = [state.lat, state.lng];

      // 1. Marker
      if (!this.satMarkers[id]) {
        const iconHtml = `
          <div style="position:relative; width:28px; height:28px; display:flex; align-items:center; justify-content:center; cursor:pointer;">
            <div style="position:absolute; inset:0; border-radius:50%; background:${color}; opacity:0.3; animation:pulseDot 2s infinite;"></div>
            <div style="position:absolute; width:14px; height:14px; border-radius:50%; background:${color}; border:2px solid #ffffff; box-shadow:0 0 10px ${color};"></div>
          </div>
        `;
        const icon = L.divIcon({
          html: iconHtml,
          className: 'sat-custom-icon',
          iconSize: [28, 28],
          iconAnchor: [14, 14]
        });

        const marker = L.marker(latlng, { icon }).addTo(this.map);
        marker.on('click', () => {
          this.activeSatId = id;
          document.getElementById('telemetry-sheet')?.classList.add('expanded');
          this.updateTelemetry();
        });
        this.satMarkers[id] = marker;
      } else {
        this.satMarkers[id].setLatLng(latlng);
      }

      // 2. Footprint Circle
      if (!this.satFootprints[id]) {
        this.satFootprints[id] = L.circle(latlng, {
          radius: state.footprintKm * 1000,
          color: color,
          weight: 1.5,
          opacity: 0.6,
          fillColor: color,
          fillOpacity: 0.08
        }).addTo(this.map);
      } else {
        this.satFootprints[id].setLatLng(latlng);
        this.satFootprints[id].setRadius(state.footprintKm * 1000);
      }

      // 3. Ground Track Polylines
      if (!this.satTracks[id]) {
        const segments = this.computeGroundTrack(sat, 90, 2);
        this.satTracks[id] = segments.map(seg => L.polyline(seg, {
          color: color,
          weight: 2,
          opacity: 0.75,
          dashArray: '4, 4'
        }).addTo(this.map));
      }
    }

    updateSolarTerminator(date) {
      // Approximate solar declination
      const dayOfYear = Math.floor((date - new Date(date.getFullYear(), 0, 0)) / 86400000);
      const declination = -23.44 * Math.cos((2 * Math.PI / 365) * (dayOfYear + 10));
      const gmtHours = date.getUTCHours() + date.getUTCMinutes() / 60;
      const subsolarLng = (12 - gmtHours) * 15;

      const termPoints = [];
      for (let lon = -180; lon <= 180; lon += 5) {
        const delta = (lon - subsolarLng) * (Math.PI / 180);
        const lat = -Math.atan(Math.cos(delta) / Math.tan(declination * (Math.PI / 180))) * (180 / Math.PI);
        termPoints.push([lat, lon]);
      }

      if (this.terminatorLayer) {
        this.map.removeLayer(this.terminatorLayer);
      }
      this.terminatorLayer = L.polyline(termPoints, {
        color: '#f59e0b',
        weight: 1.5,
        opacity: 0.5,
        dashArray: '2, 6'
      }).addTo(this.map);
    }

    updateObserverMapMarker() {
      if (!this.map || typeof L === 'undefined') return;
      if (this.observerMarker) this.map.removeLayer(this.observerMarker);

      const obsHtml = `
        <div style="width:16px; height:16px; border-radius:50%; background:#10b981; border:2px solid #ffffff; box-shadow:0 0 10px #10b981;"></div>
      `;
      this.observerMarker = L.marker([this.observer.lat, this.observer.lng], {
        icon: L.divIcon({ html: obsHtml, className: 'obs-icon', iconSize: [16, 16], iconAnchor: [8, 8] })
      }).addTo(this.map);
    }

    // ============================================================
    // 3D WebGL Globe (Three.js)
    // ============================================================
    init3DGlobe() {
      const container = document.getElementById('globe-canvas-container');
      if (!container || typeof THREE === 'undefined') return;

      const w = container.clientWidth || 360;
      const h = container.clientHeight || 500;

      this.scene3d = new THREE.Scene();
      this.camera3d = new THREE.PerspectiveCamera(45, w / h, 0.1, 1000);
      this.camera3d.position.z = 220;

      this.renderer3d = new THREE.WebGLRenderer({ antialias: true, alpha: true });
      this.renderer3d.setSize(w, h);
      this.renderer3d.setPixelRatio(Math.min(window.devicePixelRatio, 2));
      container.appendChild(this.renderer3d.domElement);

      // Ambient & Directional Light
      const ambientLight = new THREE.AmbientLight(0x404860, 2.5);
      this.scene3d.add(ambientLight);
      const sunLight = new THREE.DirectionalLight(0xffffff, 2.0);
      sunLight.position.set(150, 50, 100);
      this.scene3d.add(sunLight);

      // Earth Sphere
      const earthGeo = new THREE.SphereGeometry(60, 48, 48);
      const earthMat = new THREE.MeshPhongMaterial({
        color: 0x1e3a5f,
        emissive: 0x0a1424,
        specular: 0x334466,
        shininess: 15,
        wireframe: false
      });
      this.earth3d = new THREE.Mesh(earthGeo, earthMat);
      this.scene3d.add(this.earth3d);

      // Atmospheric Glow
      const atmosGeo = new THREE.SphereGeometry(62.5, 32, 32);
      const atmosMat = new THREE.MeshBasicMaterial({
        color: 0x38bdf8,
        transparent: true,
        opacity: 0.15,
        side: THREE.BackSide
      });
      this.scene3d.add(new THREE.Mesh(atmosGeo, atmosMat));

      // Equator Graticule
      const eqGeo = new THREE.BufferGeometry();
      const eqPts = [];
      for (let i = 0; i <= 64; i++) {
        const rad = (i / 64) * Math.PI * 2;
        eqPts.push(Math.cos(rad) * 60.5, 0, Math.sin(rad) * 60.5);
      }
      eqGeo.setAttribute('position', new THREE.Float32BufferAttribute(eqPts, 3));
      const eqMat = new THREE.LineBasicMaterial({ color: 0x334155, opacity: 0.5, transparent: true });
      this.scene3d.add(new THREE.Line(eqGeo, eqMat));

      // Touch controls
      let isDragging = false;
      let prevX = 0, prevY = 0;
      const dom = this.renderer3d.domElement;

      dom.addEventListener('pointerdown', (e) => {
        isDragging = true;
        prevX = e.clientX;
        prevY = e.clientY;
      });

      window.addEventListener('pointermove', (e) => {
        if (!isDragging) return;
        const dx = e.clientX - prevX;
        const dy = e.clientY - prevY;
        this.earth3d.rotation.y += dx * 0.008;
        this.earth3d.rotation.x += dy * 0.008;
        prevX = e.clientX;
        prevY = e.clientY;
      });

      window.addEventListener('pointerup', () => { isDragging = false; });

      // Render loop
      const animate = () => {
        requestAnimationFrame(animate);
        if (this.isGlobeRotating) {
          this.earth3d.rotation.y += 0.002;
        }
        this.renderer3d.render(this.scene3d, this.camera3d);
      };
      animate();

      // Globe action buttons
      document.getElementById('btn-globe-rotate')?.addEventListener('click', () => {
        this.isGlobeRotating = !this.isGlobeRotating;
      });
      document.getElementById('btn-globe-reset')?.addEventListener('click', () => {
        this.earth3d.rotation.set(0, 0, 0);
        this.camera3d.position.set(0, 0, 220);
      });
    }

    resize3D() {
      const container = document.getElementById('globe-canvas-container');
      if (!this.renderer3d || !container) return;
      const w = container.clientWidth;
      const h = container.clientHeight;
      this.camera3d.aspect = w / h;
      this.camera3d.updateProjectionMatrix();
      this.renderer3d.setSize(w, h);
    }

    update3DObject(sat, state, colorHex) {
      if (!this.scene3d || typeof THREE === 'undefined') return;

      const r = 60 + (state.altKm / EARTH_RADIUS_KM) * 60;
      const phi = (90 - state.lat) * (Math.PI / 180);
      const theta = (state.lng + 180) * (Math.PI / 180);

      const x = -r * Math.sin(phi) * Math.cos(theta);
      const z = r * Math.sin(phi) * Math.sin(theta);
      const y = r * Math.cos(phi);

      if (!this.satMeshes3d[sat.id]) {
        const geo = new THREE.SphereGeometry(2.4, 16, 16);
        const mat = new THREE.MeshBasicMaterial({ color: parseInt(colorHex.replace('#', '0x'), 16) });
        const mesh = new THREE.Mesh(geo, mat);
        this.scene3d.add(mesh);
        this.satMeshes3d[sat.id] = mesh;

        // Orbit ring in 3D
        const ringGeo = new THREE.BufferGeometry();
        const pts = [];
        const incRad = (sat.inclination || 51.6) * (Math.PI / 180);
        for (let i = 0; i <= 64; i++) {
          const t = (i / 64) * Math.PI * 2;
          const ox = r * Math.cos(t);
          const oy = r * Math.sin(t) * Math.sin(incRad);
          const oz = r * Math.sin(t) * Math.cos(incRad);
          pts.push(ox, oy, oz);
        }
        ringGeo.setAttribute('position', new THREE.Float32BufferAttribute(pts, 3));
        const ringMat = new THREE.LineBasicMaterial({
          color: parseInt(colorHex.replace('#', '0x'), 16),
          transparent: true,
          opacity: 0.45
        });
        const line = new THREE.Line(ringGeo, ringMat);
        this.scene3d.add(line);
        this.orbitRings3d[sat.id] = line;
      } else {
        this.satMeshes3d[sat.id].position.set(x, y, z);
      }
    }

    // ============================================================
    // Pass Predictor Engine
    // ============================================================
    setupPasses() {
      document.getElementById('btn-get-gps')?.addEventListener('click', () => {
        this.requestObserverLocation();
      });
      document.getElementById('pass-sat-select')?.addEventListener('change', (e) => {
        this.activeSatId = parseInt(e.target.value, 10);
        this.computeAndRenderPasses();
      });
    }

    requestObserverLocation() {
      if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
          (pos) => {
            this.observer.lat = Math.round(pos.coords.latitude * 1000) / 1000;
            this.observer.lng = Math.round(pos.coords.longitude * 1000) / 1000;
            this.observer.altKm = (pos.coords.altitude || 30) / 1000;
            this.observer.name = "My Device Location (GPS)";
            this.updateObserverDisplay();
            this.updateObserverMapMarker();
            this.computeAndRenderPasses();
          },
          (err) => {
            console.warn('Geolocation unavailable, using default coords', err);
            this.updateObserverDisplay();
          },
          { enableHighAccuracy: true, timeout: 6000 }
        );
      }
    }

    updateObserverDisplay() {
      const label = document.getElementById('observer-coords-label');
      if (label) {
        label.textContent = `${this.observer.name} • ${this.observer.lat.toFixed(2)}° N, ${this.observer.lng.toFixed(2)}° E`;
      }
    }

    computeAndRenderPasses() {
      const sat = root.MobileSatelliteCatalog.getById(this.activeSatId) || root.MobileSatelliteCatalog.getAll()[0];
      const listEl = document.getElementById('passes-list');
      if (!listEl || !window.satellite || !sat.line1) return;

      const satrec = sat.satrec || window.satellite.twoline2satrec(sat.line1, sat.line2);
      const obsGd = {
        latitude: this.observer.lat * (Math.PI / 180),
        longitude: this.observer.lng * (Math.PI / 180),
        height: this.observer.altKm
      };

      const now = new Date();
      const passes = [];
      let inPass = false;
      let currentPass = null;

      // Scan upcoming 24 hours at 30-second steps
      for (let s = 0; s < 86400; s += 30) {
        const t = new Date(now.getTime() + s * 1000);
        const posVel = window.satellite.propagate(satrec, t);
        if (!posVel || !posVel.position) continue;

        const gmst = window.satellite.gstime(t);
        const posEcf = window.satellite.eciToEcf(posVel.position, gmst);
        const lookAngles = window.satellite.ecfToLookAngles(obsGd, posEcf);

        const elevationDeg = (lookAngles.elevation * 180) / Math.PI;
        const azimuthDeg = (lookAngles.azimuth * 180) / Math.PI;

        if (elevationDeg >= 10) {
          if (!inPass) {
            inPass = true;
            currentPass = {
              aosTime: t,
              aosAzimuth: Math.round(azimuthDeg),
              maxElev: elevationDeg,
              maxElevTime: t,
              maxAzimuth: Math.round(azimuthDeg),
              losTime: t,
              losAzimuth: Math.round(azimuthDeg)
            };
          } else {
            if (elevationDeg > currentPass.maxElev) {
              currentPass.maxElev = elevationDeg;
              currentPass.maxElevTime = t;
              currentPass.maxAzimuth = Math.round(azimuthDeg);
            }
            currentPass.losTime = t;
            currentPass.losAzimuth = Math.round(azimuthDeg);
          }
        } else if (inPass) {
          inPass = false;
          passes.push(currentPass);
          if (passes.length >= 6) break;
        }
      }

      if (passes.length === 0) {
        listEl.innerHTML = `
          <div style="text-align:center; padding: 40px 16px; color: var(--text-muted);">
            🛰️ No visible passes above 10° elevation detected in the next 24 hours for ${sat.name}.
          </div>
        `;
        return;
      }

      listEl.innerHTML = passes.map((p, idx) => {
        const durationSec = Math.round((p.losTime - p.aosTime) / 1000);
        const durMin = Math.floor(durationSec / 60);
        const durSec = durationSec % 60;
        const maxDeg = Math.round(p.maxElev);

        const qualClass = maxDeg > 60 ? 'pass-quality-great' : maxDeg > 30 ? 'pass-quality-good' : 'pass-quality-low';
        const qualLabel = maxDeg > 60 ? 'EXCELLENT' : maxDeg > 30 ? 'GOOD' : 'FAIR';

        const diffMs = p.aosTime - now;
        const hrsIn = Math.floor(diffMs / 3600000);
        const minsIn = Math.floor((diffMs % 3600000) / 60000);
        const countdownStr = diffMs > 0 ? (hrsIn > 0 ? `In ${hrsIn}h ${minsIn}m` : `In ${minsIn} mins`) : 'Happening now';

        return `
          <div class="pass-card">
            <div class="pass-card-header">
              <div>
                <div class="pass-sat-name">${sat.name} • Pass #${idx + 1}</div>
                <div style="font-size: 0.78rem; color: var(--cyan-accent); font-weight: 600;">
                  ${p.aosTime.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} (${countdownStr})
                </div>
              </div>
              <span class="pass-quality-badge ${qualClass}">${qualLabel}</span>
            </div>
            <div style="font-size: 0.85rem; color: var(--text-main); margin-bottom: 6px;">
              <strong>Max Elevation:</strong> ${maxDeg}° at ${p.maxElevTime.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </div>
            <div style="font-size: 0.76rem; color: var(--text-muted);">
              Duration: ${durMin}m ${durSec}s  |  Rise Az: ${p.aosAzimuth}°  |  Set Az: ${p.losAzimuth}°
            </div>
            <div class="pass-sky-radar">
              <span>↗ Rise: ${this.azimuthToCompass(p.aosAzimuth)}</span>
              <span style="color:var(--cyan-accent); font-weight:700;">▲ Peak: ${maxDeg}° ${this.azimuthToCompass(p.maxAzimuth)}</span>
              <span>↘ Set: ${this.azimuthToCompass(p.losAzimuth)}</span>
            </div>
          </div>
        `;
      }).join('');
    }

    azimuthToCompass(deg) {
      const directions = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'];
      return directions[Math.round(deg / 45) % 8];
    }

    // ============================================================
    // AI Orbital Assistant & Providers
    // ============================================================
    setupAI() {
      const sendBtn = document.getElementById('btn-ai-send');
      const input = document.getElementById('ai-prompt-input');

      const handleSend = async () => {
        const text = input.value.trim();
        if (!text) return;
        input.value = '';
        this.addChatMessage('user', text);
        await this.handleAIQuery(text);
      };

      sendBtn?.addEventListener('click', handleSend);
      input?.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') handleSend();
      });

      // Settings modal
      document.getElementById('btn-open-settings')?.addEventListener('click', () => {
        document.getElementById('settings-modal')?.classList.add('active');
      });
      document.getElementById('btn-close-settings')?.addEventListener('click', () => {
        document.getElementById('settings-modal')?.classList.remove('active');
      });
      document.getElementById('btn-save-settings')?.addEventListener('click', () => {
        this.saveSettings();
        document.getElementById('settings-modal')?.classList.remove('active');
      });

      // Custom TLE modal
      document.getElementById('btn-open-tle-import')?.addEventListener('click', () => {
        document.getElementById('tle-import-modal')?.classList.add('active');
      });
      document.getElementById('btn-close-tle')?.addEventListener('click', () => {
        document.getElementById('tle-import-modal')?.classList.remove('active');
      });
      document.getElementById('btn-save-tle')?.addEventListener('click', () => {
        this.handleCustomTLEImport();
      });
    }

    addChatMessage(role, content, actions = []) {
      const history = document.getElementById('chat-history');
      if (!history) return;

      const bubble = document.createElement('div');
      bubble.className = `chat-bubble chat-bubble-${role}`;
      bubble.innerHTML = `<div>${content}</div>`;

      actions.forEach(act => {
        const btn = document.createElement('button');
        btn.className = 'ai-action-btn';
        btn.innerHTML = act.label;
        btn.onclick = act.onClick;
        bubble.appendChild(btn);
      });

      history.appendChild(bubble);
      history.scrollTop = history.scrollHeight;
    }

    async handleAIQuery(query) {
      const provider = localStorage.getItem('sattrack_ai_provider') || 'local';
      const apiKey = localStorage.getItem('sattrack_ai_key') || '';

      if (provider !== 'local' && apiKey) {
        try {
          const remoteResp = await this.queryRemoteAI(provider, apiKey, query);
          this.processAIResponse(remoteResp);
          return;
        } catch (err) {
          console.warn('Remote AI query failed, falling back to local engine:', err);
          this.addChatMessage('ai', `⚠️ Remote query failed (${err.message}). Using local SGP4 discovery engine:`);
        }
      }

      // Local Rule & Natural Query Engine
      const localResult = this.localOrbitalDiscovery(query);
      this.processAIResponse(localResult);
    }

    localOrbitalDiscovery(query) {
      const q = query.toLowerCase();
      const allSats = root.MobileSatelliteCatalog.getAll();

      if (q.includes('weather') || q.includes('climate')) {
        const sats = allSats.filter(s => s.category === 'weather' || s.category === 'earth');
        return {
          text: `Found ${sats.length} meteorological & Earth observation satellites. Equipped with multispectral imagers and atmospheric sounders.`,
          recommendedSatIds: sats.slice(0, 3).map(s => s.id)
        };
      }

      if (q.includes('gps') || q.includes('navigation') || q.includes('glonass')) {
        const sats = allSats.filter(s => s.category === 'gps');
        return {
          text: `Found ${sats.length} GNSS navigation satellites operating in Medium Earth Orbit (~20,200 km altitude, 12-hour period).`,
          recommendedSatIds: sats.slice(0, 3).map(s => s.id)
        };
      }

      if (q.includes('station') || q.includes('iss') || q.includes('human') || q.includes('crew')) {
        const sats = allSats.filter(s => s.category === 'stations');
        return {
          text: `Found ${sats.length} continuously inhabited space stations currently in Low Earth Orbit (ISS and Tiangong CSS).`,
          recommendedSatIds: sats.map(s => s.id)
        };
      }

      if (q.includes('starlink') || q.includes('megaconstellation') || q.includes('internet')) {
        const sats = allSats.filter(s => s.category === 'starlink');
        return {
          text: `Found ${sats.length} constellation satellites providing global low-latency broadband in 550 km shell orbits.`,
          recommendedSatIds: sats.slice(0, 3).map(s => s.id)
        };
      }

      if (q.includes('high') || q.includes('alt') || q.includes('altitude') || q.includes('geo')) {
        const sats = allSats.filter(s => s.alt_km > 20000);
        return {
          text: `Found ${sats.length} high-altitude spacecraft in MEO, GEO, and Highly Elliptical Orbits (HEO).`,
          recommendedSatIds: sats.slice(0, 3).map(s => s.id)
        };
      }

      // Default smart fallback
      const matching = allSats.filter(s => s.name.toLowerCase().includes(q) || String(s.id).includes(q));
      if (matching.length > 0) {
        return {
          text: `Matched ${matching.length} spacecraft in catalog for query "${query}".`,
          recommendedSatIds: matching.slice(0, 3).map(s => s.id)
        };
      }

      return {
        text: `The SGP4 orbital propagator is running locally. You can track any satellite from the Catalog, inspect real-time 2D/3D ground tracks, or configure an optional remote AI key (Gemini/OpenAI) in Settings.`,
        recommendedSatIds: [25544]
      };
    }

    async queryRemoteAI(provider, apiKey, prompt) {
      if (provider === 'gemini') {
        const url = `https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${apiKey}`;
        const res = await fetch(url, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            contents: [{ parts: [{ text: `You are an orbital mechanics and satellite expert. Answer succinctly: ${prompt}` }] }]
          })
        });
        if (!res.ok) throw new Error(`Gemini HTTP error ${res.status}`);
        const data = await res.json();
        const text = data.candidates?.[0]?.content?.parts?.[0]?.text || 'No response from Gemini';
        return { text, recommendedSatIds: this.extractSatIdsFromText(text) };
      }

      if (provider === 'openai') {
        const url = 'https://api.openai.com/v1/chat/completions';
        const res = await fetch(url, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${apiKey}`
          },
          body: JSON.stringify({
            model: 'gpt-4o-mini',
            messages: [{ role: 'user', content: prompt }]
          })
        });
        if (!res.ok) throw new Error(`OpenAI HTTP error ${res.status}`);
        const data = await res.json();
        const text = data.choices?.[0]?.message?.content || 'No response from OpenAI';
        return { text, recommendedSatIds: this.extractSatIdsFromText(text) };
      }

      throw new Error(`Unsupported provider ${provider}`);
    }

    extractSatIdsFromText(text) {
      const ids = [];
      const allSats = root.MobileSatelliteCatalog.getAll();
      allSats.forEach(s => {
        if (text.includes(String(s.id)) || text.toUpperCase().includes(s.name.toUpperCase())) {
          ids.push(s.id);
        }
      });
      return ids.slice(0, 3);
    }

    processAIResponse(res) {
      const actions = [];
      if (res.recommendedSatIds && res.recommendedSatIds.length > 0) {
        actions.push({
          label: '🎯 Track on Map Now',
          onClick: () => {
            res.recommendedSatIds.forEach(id => {
              if (!this.trackedSatIds.includes(id)) this.trackedSatIds.push(id);
            });
            this.activeSatId = res.recommendedSatIds[0];
            this.switchTab('track');
            this.updateTelemetry();
          }
        });
      }
      this.addChatMessage('ai', res.text, actions);
    }

    // ============================================================
    // Catalog Management & UI
    // ============================================================
    setupSearch() {
      const input = document.getElementById('catalog-search-input');
      input?.addEventListener('input', () => {
        this.renderCatalogList();
      });

      const chips = document.querySelectorAll('.category-chip');
      chips.forEach(chip => {
        chip.addEventListener('click', () => {
          chips.forEach(c => c.classList.remove('active'));
          chip.classList.add('active');
          this.renderCatalogList();
        });
      });

      document.getElementById('btn-sync-celestrak')?.addEventListener('click', async () => {
        const btn = document.getElementById('btn-sync-celestrak');
        const originalText = btn.textContent;
        btn.textContent = 'Syncing…';
        try {
          const res = await root.MobileSatelliteCatalog.syncCelesTrakGroup('stations');
          btn.textContent = `Synced (${res.count})!`;
          this.renderCatalogList();
          this.updateSyncInfo();
          setTimeout(() => { btn.textContent = originalText; }, 2500);
        } catch (e) {
          btn.textContent = 'Sync Failed';
          setTimeout(() => { btn.textContent = originalText; }, 2500);
        }
      });
    }

    renderCatalogList() {
      const container = document.getElementById('catalog-list');
      if (!container) return;

      const q = document.getElementById('catalog-search-input')?.value || '';
      const activeChip = document.querySelector('.category-chip.active');
      const category = activeChip?.getAttribute('data-cat') || 'all';

      const sats = root.MobileSatelliteCatalog.search(q, category);

      if (sats.length === 0) {
        container.innerHTML = `
          <div style="text-align:center; padding: 40px 16px; color: var(--text-muted);">
            🔍 No satellites matching "${q}"
          </div>
        `;
        return;
      }

      container.innerHTML = sats.map(sat => {
        const isTracking = this.trackedSatIds.includes(sat.id);
        return `
          <div class="sat-card">
            <div class="sat-card-left">
              <div class="sat-card-title">${sat.name}</div>
              <div class="sat-card-meta">
                <span class="orbit-badge">${sat.orbit || 'LEO'}</span>
                <span>NORAD ${sat.id}</span>
                <span>Alt: ${sat.alt_km || 400} km</span>
              </div>
            </div>
            <button class="btn-track ${isTracking ? 'tracking' : ''}" data-id="${sat.id}">
              ${isTracking ? '✓ Tracking' : '+ Track'}
            </button>
          </div>
        `;
      }).join('');

      container.querySelectorAll('.btn-track').forEach(btn => {
        btn.addEventListener('click', () => {
          const id = parseInt(btn.getAttribute('data-id'), 10);
          if (this.trackedSatIds.includes(id)) {
            this.trackedSatIds = this.trackedSatIds.filter(x => x !== id);
          } else {
            this.trackedSatIds.push(id);
            this.activeSatId = id;
          }
          this.renderCatalogList();
          this.updateTelemetry();
        });
      });
    }

    updateSyncInfo() {
      const syncEl = document.getElementById('sync-info-text');
      if (!syncEl) return;
      const last = root.MobileSatelliteCatalog.getLastSyncTime();
      if (last) {
        syncEl.textContent = `Catalog updated: ${last.toLocaleDateString()} ${last.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
      } else {
        syncEl.textContent = 'Built-in verified offline ephemeris primed.';
      }
    }

    handleCustomTLEImport() {
      const name = document.getElementById('custom-tle-name')?.value || 'CUSTOM';
      const l1 = document.getElementById('custom-tle-line1')?.value || '';
      const l2 = document.getElementById('custom-tle-line2')?.value || '';

      try {
        const sat = root.MobileSatelliteCatalog.importTLE(name, l1, l2);
        this.trackedSatIds.push(sat.id);
        this.activeSatId = sat.id;
        document.getElementById('tle-import-modal')?.classList.remove('active');
        this.renderCatalogList();
        this.switchTab('track');
        this.updateTelemetry();
      } catch (err) {
        alert(err.message);
      }
    }

    // ============================================================
    // HUD & Settings
    // ============================================================
    renderHUD(sat, state, color) {
      const nameEl = document.getElementById('hud-sat-name');
      const noradEl = document.getElementById('hud-sat-norad');
      const dotEl = document.getElementById('hud-sat-color');

      if (nameEl) nameEl.textContent = sat.name;
      if (noradEl) noradEl.textContent = `NORAD ${sat.id} • ${sat.orbit || 'LEO'}`;
      if (dotEl) {
        dotEl.style.background = color;
        dotEl.style.boxShadow = `0 0 10px ${color}`;
      }

      document.getElementById('hud-lat')?.replaceChildren(document.createTextNode(`${Math.abs(state.lat).toFixed(2)}° ${state.lat >= 0 ? 'N' : 'S'}`));
      document.getElementById('hud-lng')?.replaceChildren(document.createTextNode(`${Math.abs(state.lng).toFixed(2)}° ${state.lng >= 0 ? 'E' : 'W'}`));
      document.getElementById('hud-alt')?.replaceChildren(document.createTextNode(`${state.altKm.toLocaleString()} km`));
      document.getElementById('hud-vel')?.replaceChildren(document.createTextNode(`${state.velKmS} km/s`));
      document.getElementById('hud-footprint')?.replaceChildren(document.createTextNode(`${state.footprintKm.toLocaleString()} km`));
      document.getElementById('hud-inc')?.replaceChildren(document.createTextNode(`${sat.inclination || 51.6}°`));
    }

    loadSettings() {
      const provider = localStorage.getItem('sattrack_ai_provider') || 'local';
      const key = localStorage.getItem('sattrack_ai_key') || '';
      const select = document.getElementById('setting-ai-provider');
      const keyInput = document.getElementById('setting-ai-key');
      if (select) select.value = provider;
      if (keyInput) keyInput.value = key;
    }

    saveSettings() {
      const select = document.getElementById('setting-ai-provider');
      const keyInput = document.getElementById('setting-ai-key');
      if (select) localStorage.setItem('sattrack_ai_provider', select.value);
      if (keyInput) localStorage.setItem('sattrack_ai_key', keyInput.value.trim());
    }
  }

  // Auto-init on page load
  document.addEventListener('DOMContentLoaded', () => {
    root.App = new MobileTrackerApp();
    root.App.init();
  });

})(window);
