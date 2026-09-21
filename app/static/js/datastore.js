window.SatDatastore = {
  toggleEngine: function () {
    const engine = document.querySelector('input[name="engine"]:checked');
    const sqlite = document.getElementById("ds-sqlite-fields");
    const postgres = document.getElementById("ds-postgres-fields");
    if (!engine || !sqlite || !postgres) return;
    const isPg = engine.value === "postgresql";
    sqlite.style.display = isPg ? "none" : "";
    postgres.style.display = isPg ? "" : "none";
    document.getElementById("ds-card-sqlite")?.classList.toggle("is-selected", !isPg);
    document.getElementById("ds-card-postgres")?.classList.toggle("is-selected", isPg);
  },

  formPayload: function () {
    const form = document.getElementById("datastore-form");
    const data = {};
    new FormData(form).forEach((value, key) => {
      data[key] = value;
    });
    return data;
  },

  setStatus: function (ok, message) {
    const el = document.getElementById("ds-status");
    if (!el) return;
    el.textContent = message || "";
    el.className = "ds-status " + (ok ? "ds-status--ok" : "ds-status--err");
  },

  testConnection: async function () {
    const form = document.getElementById("datastore-form");
    const url = form?.dataset.testUrl;
    const btn = document.getElementById("ds-test-btn");
    if (!url) return;
    if (btn) btn.disabled = true;
    this.setStatus(true, "Testing connection…");
    try {
      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json", "Accept": "application/json" },
        body: JSON.stringify(this.formPayload()),
      });
      const data = await res.json();
      this.setStatus(Boolean(data.ok), data.message || (data.ok ? "Connected" : "Connection failed"));
    } catch (err) {
      this.setStatus(false, String(err));
    } finally {
      if (btn) btn.disabled = false;
    }
  },
};

document.addEventListener("DOMContentLoaded", function () {
  if (window.SatDatastore) window.SatDatastore.toggleEngine();
});
