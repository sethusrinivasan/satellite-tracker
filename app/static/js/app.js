// ── Drop Zone ──────────────────────────────────────────────────────────────
const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const filePreview = document.getElementById('file-preview');
const previewName = document.getElementById('file-preview-name');
const previewSize = document.getElementById('file-preview-size');
const fileRemove = document.getElementById('file-remove');
const uploadBtn = document.getElementById('upload-btn');

function formatBytes(bytes) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / 1048576).toFixed(1) + ' MB';
}

function showPreview(file) {
  if (!previewName) return;
  previewName.textContent = file.name;
  previewSize.textContent = formatBytes(file.size);
  filePreview.hidden = false;
  if (dropZone) dropZone.hidden = true;
  if (uploadBtn) uploadBtn.disabled = false;
}

function clearFile() {
  if (fileInput) fileInput.value = '';
  if (filePreview) filePreview.hidden = true;
  if (dropZone) dropZone.hidden = false;
  if (uploadBtn) uploadBtn.disabled = true;
}

if (fileInput) {
  fileInput.addEventListener('change', () => {
    if (fileInput.files[0]) showPreview(fileInput.files[0]);
  });
}

if (dropZone) {
  dropZone.addEventListener('click', (e) => {
    if (e.target.closest('label, input, button')) return;
    fileInput && fileInput.click();
  });
  dropZone.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') fileInput && fileInput.click(); });

  ['dragenter','dragover'].forEach(evt => {
    dropZone.addEventListener(evt, e => { e.preventDefault(); dropZone.classList.add('drag-over'); });
  });
  ['dragleave','drop'].forEach(evt => {
    dropZone.addEventListener(evt, e => { e.preventDefault(); dropZone.classList.remove('drag-over'); });
  });
  dropZone.addEventListener('drop', e => {
    const file = e.dataTransfer.files[0];
    if (file && fileInput) {
      const dt = new DataTransfer();
      dt.items.add(file);
      fileInput.files = dt.files;
      showPreview(file);
    }
  });
}

if (fileRemove) fileRemove.addEventListener('click', clearFile);

// ── Global Long-Running Operation Progress Modal (SatProgress) ──────────────
const SatProgress = (function() {
  const overlay = document.getElementById('sat-global-splash');
  const titleEl = document.getElementById('sat-splash-title');
  const subEl = document.getElementById('sat-splash-subtitle');
  const iconEl = document.getElementById('sat-splash-icon');
  const barEl = document.getElementById('sat-splash-bar');
  const msgEl = document.getElementById('sat-splash-msg');
  const fallbackBox = document.getElementById('sat-splash-fallback');
  const fallbackText = document.getElementById('sat-splash-fallback-text');

  let stepTimer = null;
  let fallbackTimer = null;
  let currentMsgIndex = 0;

  function show(options) {
    if (!overlay) return;
    options = options || {};

    if (titleEl) titleEl.textContent = options.title || "Processing Operation";
    if (subEl) subEl.textContent = options.subtitle || "Please wait while satellite telemetry is processed…";
    if (iconEl && options.icon) iconEl.textContent = options.icon;
    if (barEl) barEl.style.width = (options.startProgress || 22) + '%';

    const messages = options.messages || [
      "Initializing operation…",
      "Validating telemetry records…",
      "Persisting updates to datastore…"
    ];

    currentMsgIndex = 0;
    if (msgEl) msgEl.textContent = messages[0];

    // Hide fallback initially
    if (fallbackBox) fallbackBox.hidden = true;
    if (fallbackText && options.fallbackMessage) {
      fallbackText.textContent = options.fallbackMessage;
    }

    // Progressively cycle subtle initialization messages
    clearInterval(stepTimer);
    const interval = options.stepInterval || 2200;
    stepTimer = setInterval(function() {
      currentMsgIndex++;
      if (currentMsgIndex < messages.length) {
        if (msgEl) {
          msgEl.style.opacity = '0';
          setTimeout(function() {
            msgEl.textContent = messages[currentMsgIndex];
            msgEl.style.opacity = '1';
          }, 180);
        }
        if (barEl) {
          const stepPct = Math.min(94, 22 + Math.round((currentMsgIndex / messages.length) * 70));
          barEl.style.width = stepPct + '%';
        }
      }
    }, interval);

    // Subtly display the fallback message if operation takes time
    clearTimeout(fallbackTimer);
    const fbDelay = options.fallbackDelay || 3800;
    fallbackTimer = setTimeout(function() {
      if (fallbackBox) {
        fallbackBox.hidden = false;
      }
    }, fbDelay);

    overlay.hidden = false;
    void overlay.offsetWidth;
    overlay.classList.add('is-active');
  }

  function setProgress(pct) {
    if (barEl) barEl.style.width = Math.max(0, Math.min(100, pct)) + '%';
  }

  function updateMessage(msg) {
    if (msgEl) {
      msgEl.style.opacity = '0';
      setTimeout(function() {
        msgEl.textContent = msg;
        msgEl.style.opacity = '1';
      }, 150);
    }
  }

  function hide() {
    clearInterval(stepTimer);
    clearTimeout(fallbackTimer);
    if (!overlay) return;
    if (barEl) barEl.style.width = '100%';
    overlay.classList.remove('is-active');
    setTimeout(function() {
      overlay.hidden = true;
    }, 300);
  }

  return {
    show: show,
    hide: hide,
    setProgress: setProgress,
    updateMessage: updateMessage
  };
})();

window.SatProgress = SatProgress;

// Upload form loading state
const uploadForm = document.getElementById('upload-form');
if (uploadForm) {
  uploadForm.addEventListener('submit', () => {
    if (uploadBtn) {
      uploadBtn.disabled = true;
      uploadBtn.innerHTML = '<span style="display:inline-flex;align-items:center;gap:8px"><svg style="animation:spin 1s linear infinite" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 11-18 0 9 9 0 0118 0"/></svg> Parsing &amp; Saving…</span>';
    }
    SatProgress.show({
      title: "Ingesting Satellite Dataset",
      subtitle: "Parsing Two-Line Element (TLE) records and orbital physics",
      icon: "📄",
      messages: [
        "Reading uploaded ephemeris payload…",
        "Validating TLE checksums & orbital epochs…",
        "Executing SGP4 orbital element ingestion…",
        "Committing records into configured datastore…"
      ],
      fallbackMessage: "Batched Transaction Active: Large ephemeris sets run in indexed batches to ensure datastore consistency without dropping connections.",
      fallbackDelay: 3800,
      stepInterval: 2200
    });
  });
}

// ── Ingest Mode Switcher (URL vs File) ─────────────────────────────────────────
const tabUrl = document.getElementById('tab-btn-url');
const tabFile = document.getElementById('tab-btn-file');
const panelUrl = document.getElementById('panel-url');
const panelFile = document.getElementById('panel-file');

function setIngestTab(mode) {
  if (!tabUrl || !tabFile || !panelUrl || !panelFile) return;
  if (mode === 'url') {
    tabUrl.classList.add('active');
    tabUrl.setAttribute('aria-selected', 'true');
    tabFile.classList.remove('active');
    tabFile.setAttribute('aria-selected', 'false');
    panelUrl.hidden = false;
    panelFile.hidden = true;
  } else {
    tabFile.classList.add('active');
    tabFile.setAttribute('aria-selected', 'true');
    tabUrl.classList.remove('active');
    tabUrl.setAttribute('aria-selected', 'false');
    panelFile.hidden = false;
    panelUrl.hidden = true;
  }
}

if (tabUrl && tabFile) {
  tabUrl.addEventListener('click', () => setIngestTab('url'));
  tabFile.addEventListener('click', () => setIngestTab('file'));
}

// ── CelesTrak URL Preset Chips & Submit State ──────────────────────────────────
const tleUrlInput = document.getElementById('tle-url-input');
const presetChips = document.querySelectorAll('.preset-chip');
const urlImportForm = document.getElementById('url-import-form');
const urlImportBtn = document.getElementById('url-import-btn');

presetChips.forEach(chip => {
  chip.addEventListener('click', () => {
    const targetUrl = chip.getAttribute('data-url');
    if (tleUrlInput && targetUrl) {
      tleUrlInput.value = targetUrl;
      presetChips.forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
    }
  });
});

if (urlImportForm && urlImportBtn) {
  urlImportForm.addEventListener('submit', (e) => {
    const progressCard = document.getElementById('celestrak-progress-card');
    const targetUrl = (tleUrlInput ? tleUrlInput.value : '').trim();

    // If dedicated in-page progress card is present, provide rich real-time UX
    if (progressCard) {
      e.preventDefault();
      urlImportBtn.disabled = true;
      urlImportBtn.innerHTML = '<span style="display:inline-flex;align-items:center;gap:8px"><svg style="animation:spin 1s linear infinite" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 11-18 0 9 9 0 0118 0"/></svg> Fetching &amp; Parsing CelesTrak…</span>';

      progressCard.hidden = false;
      const targetUrlEl = document.getElementById('cp-target-url');
      if (targetUrlEl && targetUrl) {
        targetUrlEl.textContent = targetUrl;
      }

      const barEl = document.getElementById('cp-bar');
      const timerEl = document.getElementById('cp-timer');
      const step1 = document.getElementById('cp-step-1');
      const step2 = document.getElementById('cp-step-2');
      const step3 = document.getElementById('cp-step-3');
      const step4 = document.getElementById('cp-step-4');
      const fallbackTextEl = document.getElementById('cp-fallback-text');
      const resultBanner = document.getElementById('cp-result-banner');
      const resultDetails = document.getElementById('cp-result-details');

      if (resultBanner) resultBanner.hidden = true;
      if (barEl) barEl.style.width = '18%';

      // Reset step classes
      [step1, step2, step3, step4].forEach((s, idx) => {
        if (!s) return;
        s.className = 'cp-step ' + (idx === 0 ? 'is-active' : 'is-pending');
      });

      const startTime = Date.now();
      const clockInterval = setInterval(() => {
        const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
        if (timerEl) timerEl.textContent = `⏱️ ${elapsed}s`;
        const elapsedNum = parseFloat(elapsed);

        if (elapsedNum >= 1.2 && step1 && step2 && step1.classList.contains('is-active')) {
          step1.className = 'cp-step is-done';
          step2.className = 'cp-step is-active';
          if (barEl) barEl.style.width = '38%';
        }
        if (elapsedNum >= 2.8 && step2 && step3 && step2.classList.contains('is-active')) {
          step2.className = 'cp-step is-done';
          step3.className = 'cp-step is-active';
          if (barEl) barEl.style.width = '64%';
        }
        if (elapsedNum >= 4.5 && step3 && step4 && step3.classList.contains('is-active')) {
          step3.className = 'cp-step is-done';
          step4.className = 'cp-step is-active';
          if (barEl) barEl.style.width = '86%';
        }
        if (elapsedNum >= 6.0 && fallbackTextEl) {
          fallbackTextEl.innerHTML = '<strong>High-Volume Constellation Ingest:</strong> Large orbital dataset in transit (approx. 3,000–8,000 satellites). Executing SGP4 orbital calculations and batch datastore transactions with ACID safety…';
        }
      }, 100);

      const formData = new FormData(urlImportForm);
      fetch(urlImportForm.action, {
        method: 'POST',
        body: formData,
        headers: {
          'Accept': 'application/json',
          'X-Requested-With': 'XMLHttpRequest'
        }
      })
      .then(res => res.json())
      .then(data => {
        clearInterval(clockInterval);
        if (barEl) barEl.style.width = '100%';
        [step1, step2, step3, step4].forEach(s => { if (s) s.className = 'cp-step is-done'; });

        if (data.success) {
          if (data.notice && fallbackTextEl) {
            fallbackTextEl.innerHTML = `<strong>Resilience Active:</strong> ${data.notice}`;
          }
          if (resultBanner && resultDetails) {
            resultBanner.hidden = false;
            resultBanner.style.borderColor = 'rgba(16, 185, 129, 0.4)';
            resultBanner.style.background = 'rgba(16, 185, 129, 0.12)';
            const headerEl = document.getElementById('cp-result-header');
            if (headerEl) headerEl.textContent = '✅ Ingestion Complete!';
            resultDetails.innerHTML = `<strong>${data.created_count}</strong> new satellites created • <strong>${data.updated_count}</strong> updated • Total <strong>${data.total_count || data.parsed_count}</strong> entities in catalog.`;
          }
          setTimeout(() => {
            window.location.href = data.redirect_url || '/report';
          }, 2400);
        } else {
          if (resultBanner && resultDetails) {
            resultBanner.hidden = false;
            resultBanner.style.borderColor = 'rgba(239, 68, 68, 0.4)';
            resultBanner.style.background = 'rgba(239, 68, 68, 0.12)';
            const headerEl = document.getElementById('cp-result-header');
            if (headerEl) {
              headerEl.textContent = '❌ Ingestion Notice';
              headerEl.style.color = 'var(--error)';
            }
            resultDetails.textContent = data.error || 'Failed to fetch from CelesTrak. Please verify the URL and try again.';
          }
          urlImportBtn.disabled = false;
          urlImportBtn.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="2" y1="12" x2="22" y2="12"></line><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path></svg> Fetch &amp; Import from CelesTrak';
        }
      })
      .catch(err => {
        clearInterval(clockInterval);
        // Fallback: submit standard form if AJAX fails
        urlImportForm.submit();
      });

    } else {
      // Fallback to global SatProgress modal
      urlImportBtn.disabled = true;
      urlImportBtn.innerHTML = '<span style="display:inline-flex;align-items:center;gap:8px"><svg style="animation:spin 1s linear infinite" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 11-18 0 9 9 0 0118 0"/></svg> Fetching &amp; Parsing CelesTrak…</span>';
      SatProgress.show({
        title: "Importing CelesTrak Ephemeris",
        subtitle: "Connecting to CelesTrak orbital telemetry repository",
        icon: "🛰️",
        messages: [
          "Initiating HTTPS request to CelesTrak ephemeris service…",
          "Streaming orbital Two-Line Element (TLE) records…",
          "Deduplicating NORAD catalog identifiers & epoch timestamps…",
          "Committing satellite telemetry into database…"
        ],
        fallbackMessage: "Resilience Fallback Active: If CelesTrak public servers return HTTP 403 cooldown or time out, the local cached ephemeris snapshot is automatically ingested.",
        fallbackDelay: 3500,
        stepInterval: 2000
      });
    }
  });
}

// Reseed Kaggle button loading state
const reseedBtn = document.getElementById('btn-reseed');
if (reseedBtn) {
  const reseedForm = reseedBtn.closest('form');
  if (reseedForm) {
    reseedForm.addEventListener('submit', () => {
      SatProgress.show({
        title: "Reseeding Satellite Datastore",
        subtitle: "Importing Kaggle Satellite Telemetry Dataset",
        icon: "🔄",
        messages: [
          "Checking dataset presence in data/kaggle_satellites.csv…",
          "Ingesting catalog entries, inclinations, and apogee elements…",
          "Rebuilding geospatial & orbital query indices…"
        ],
        fallbackMessage: "Seed Fallback Active: If the Kaggle dataset CSV is absent, the bundled demo satellite catalog is populated automatically.",
        fallbackDelay: 3500,
        stepInterval: 2000
      });
    });
  }
}

// ── TLE Raw toggle ──────────────────────────────────────────────────────────
document.querySelectorAll('.tle-toggle').forEach(btn => {
  btn.addEventListener('click', () => {
    const targetId = btn.getAttribute('data-target');
    const panel = document.getElementById(targetId);
    if (!panel) return;
    const isHidden = panel.hidden;
    panel.hidden = !isHidden;
    btn.textContent = isHidden ? 'Hide TLE' : 'Show TLE';
    btn.setAttribute('aria-expanded', isHidden ? 'true' : 'false');
  });
});

// ── Auto-dismiss flash messages ─────────────────────────────────────────────
document.querySelectorAll('.flash').forEach(flash => {
  setTimeout(() => flash.remove(), 6000);
});
