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
  dropZone.addEventListener('click', () => fileInput && fileInput.click());
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

// Upload form loading state
const uploadForm = document.getElementById('upload-form');
if (uploadForm) {
  uploadForm.addEventListener('submit', () => {
    if (uploadBtn) {
      uploadBtn.disabled = true;
      uploadBtn.innerHTML = '<span style="display:inline-flex;align-items:center;gap:8px"><svg style="animation:spin 1s linear infinite" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 11-18 0 9 9 0 0118 0"/></svg> Parsing & Saving…</span>';
    }
  });
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
