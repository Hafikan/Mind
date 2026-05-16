(function () {
  "use strict";

  const API_BASE = "/career/api/";
  const DEEP_PATH = "/career/deep/";

  function getCookie(name) {
    const v = document.cookie.split("; ").find((r) => r.startsWith(name + "="));
    return v ? decodeURIComponent(v.split("=")[1]) : null;
  }

  async function api(url, opts = {}) {
    const headers = Object.assign(
      { "Content-Type": "application/json", "X-CSRFToken": getCookie("csrftoken") || "" },
      opts.headers || {}
    );
    const res = await fetch(url, Object.assign({ credentials: "same-origin" }, opts, { headers }));
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new Error(`${res.status} ${res.statusText} — ${text}`);
    }
    if (res.status === 204) return null;
    return res.json();
  }

  let phases = [];
  let categories = [];
  let tasks = [];
  let deepDives = [];
  let currentCat = "all";
  let currentType = "all";
  let currentSearch = "";

  function unwrap(data) {
    return Array.isArray(data) ? data : data.results || [];
  }

  async function loadAll() {
    const [p, c, t, d] = await Promise.all([
      api(API_BASE + "phases/"),
      api(API_BASE + "categories/"),
      api(API_BASE + "tasks/"),
      api(API_BASE + "deep-dives/"),
    ]);
    phases = unwrap(p);
    categories = unwrap(c);
    tasks = unwrap(t);
    deepDives = unwrap(d);
  }

  function resolveColor(token) {
    if (!token) return "var(--text-muted)";
    if (token.startsWith("--")) return `var(${token})`;
    if (token.startsWith("var(") || token.startsWith("#") || token.startsWith("rgb")) return token;
    return `var(--accent-${token})`;
  }

  function renderCategoryFilters() {
    const root = document.getElementById("category-filters");
    root.innerHTML = "";
    categories.forEach((cat) => {
      const btn = document.createElement("button");
      btn.className = "filter-btn";
      btn.dataset.cat = cat.key;
      btn.textContent = cat.name;
      btn.style.borderLeft = `3px solid ${resolveColor(cat.color)}`;
      btn.addEventListener("click", () => {
        document.querySelectorAll(".filter-btn[data-cat]").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        currentCat = cat.key;
        applyFilters();
      });
      root.appendChild(btn);
    });
  }

  function renderLegend() {
    const legend = document.getElementById("legend");
    legend.querySelectorAll(".legend-item.cat").forEach((n) => n.remove());
    categories.forEach((cat) => {
      const item = document.createElement("div");
      item.className = "legend-item cat";
      item.innerHTML = `<span class="legend-dot" style="background:${resolveColor(cat.color)};"></span> ${cat.name}`;
      legend.insertBefore(item, legend.querySelector(".legend-item:last-child"));
    });
  }

  function renderDeepDiveNav() {
    const nav = document.getElementById("deep-dive-nav");
    nav.querySelectorAll(".nav-item").forEach((n) => n.remove());
    const empty = document.getElementById("dd-empty");
    if (!deepDives.length) {
      empty.style.display = "";
      return;
    }
    empty.style.display = "none";
    deepDives.forEach((d) => {
      const a = document.createElement("a");
      a.className = "nav-item";
      a.href = DEEP_PATH + d.slug + "/";
      a.textContent = d.title;
      nav.appendChild(a);
    });
  }

  function renderMatrix() {
    const matrix = document.getElementById("matrix-grid");
    const empty = document.getElementById("empty-state");
    matrix.innerHTML = "";

    if (!phases.length || !categories.length) {
      matrix.style.display = "none";
      empty.style.display = "";
      return;
    }
    matrix.style.display = "";
    empty.style.display = "none";

    matrix.style.gridTemplateColumns = `140px repeat(${phases.length}, 1fr)`;
    matrix.style.minWidth = `${140 + phases.length * 220}px`;

    const corner = document.createElement("div");
    corner.className = "matrix-cell header-cell";
    corner.style.background = "var(--bg-elevated)";
    corner.innerHTML = '<div style="font-size:11px;color:var(--text-dim);">Kategori \\ Faz</div>';
    matrix.appendChild(corner);

    phases.forEach((p, idx) => {
      const cell = document.createElement("div");
      cell.className = "matrix-cell header-cell";
      const range = formatDateRange(p.start_date, p.due_date);
      cell.innerHTML = `<div class="phase-num">Faz ${idx + 1}</div><div class="phase-time">${escapeHtml(range)}</div><div class="phase-theme">${escapeHtml(p.theme || "")}</div>`;
      matrix.appendChild(cell);
    });

    categories.forEach((cat) => {
      const rowH = document.createElement("div");
      rowH.className = "row-header";
      rowH.dataset.cat = cat.key;
      rowH.innerHTML = `<div class="row-icon" style="background:${resolveColor(cat.color)};"></div><div>${escapeHtml(cat.name)}</div>`;
      matrix.appendChild(rowH);

      phases.forEach((phase) => {
        const cell = document.createElement("div");
        cell.className = "matrix-cell";
        cell.dataset.cat = cat.key;
        cell.dataset.phaseId = phase.id;

        const cellTasks = tasks.filter((t) => t.category === cat.id && t.phase === phase.id);
        cellTasks.forEach((task) => cell.appendChild(buildTaskChip(task, cat)));

        const addBtn = document.createElement("button");
        addBtn.className = "add-task-btn";
        addBtn.textContent = "+ görev";
        addBtn.addEventListener("click", (e) => {
          e.stopPropagation();
          openTaskCreate(phase.id, cat.id);
        });
        cell.appendChild(addBtn);

        matrix.appendChild(cell);
      });
    });
  }

  function buildTaskChip(task, cat) {
    const chip = document.createElement("div");
    chip.className = "task-chip";
    chip.dataset.taskId = task.id;
    chip.style.borderLeft = `2px solid ${resolveColor(cat.color)}`;
    if (task.completed) chip.classList.add("completed");

    const badges = [];
    if (task.type === "book") badges.push('<span class="badge book">kitap</span>');
    if (task.type === "project") badges.push('<span class="badge project">proje</span>');
    if (task.type === "cert") badges.push('<span class="badge cert">sertifika</span>');
    if ((task.weight || 0) >= 5) badges.push('<span class="badge high">öncelik</span>');
    if (task.deep_dive) badges.push('<span class="badge deep">deep ↓</span>');

    chip.innerHTML =
      '<div class="checkbox" data-toggle></div>' +
      '<div class="text"><div>' +
      escapeHtml(task.title) +
      "</div>" +
      (badges.length ? '<div class="badges">' + badges.join("") + "</div>" : "") +
      "</div>";

    chip.addEventListener("click", (e) => {
      if (e.target.dataset.toggle !== undefined) return;
      openTaskModal(task);
    });
    const cb = chip.querySelector(".checkbox");
    cb.addEventListener("click", async (e) => {
      e.stopPropagation();
      try {
        const res = await api(API_BASE + `tasks/${task.id}/toggle/`, { method: "PATCH" });
        task.completed = res.completed;
        chip.classList.toggle("completed", res.completed);
        updateStats();
      } catch (err) {
        console.error(err);
      }
    });
    return chip;
  }

  function openTaskModal(task) {
    const phase = phases.find((p) => p.id === task.phase);
    const cat = categories.find((c) => c.id === task.category);
    const dd = task.deep_dive ? deepDives.find((d) => d.id === task.deep_dive) : null;
    const content = document.getElementById("modal-content");

    let resourcesHTML = "";
    if (task.resources && task.resources.length) {
      resourcesHTML =
        "<section><h3>Kaynaklar</h3><div class=\"resource-list\">" +
        task.resources
          .map(
            (r) =>
              `<div class="resource"><div class="resource-title">${escapeHtml(r.title)}</div><div class="resource-meta">${escapeHtml(r.meta || "")}</div></div>`
          )
          .join("") +
        "</div></section>";
    }
    const ddHTML = dd
      ? `<section><h3>Derin alt yapı</h3><a href="${DEEP_PATH + dd.slug}/" class="deep-link">↓ ${escapeHtml(dd.title)} — detaylı bölüme git</a></section>`
      : "";
    const aiHTML = task.ai_usage
      ? `<section><h3>AI nasıl kullanılır</h3><div class="ai-block">${escapeHtml(task.ai_usage)}</div></section>`
      : "";

    const catColor = cat ? resolveColor(cat.color) : "var(--text-muted)";
    const editBtn = `<a href="/career/manage/?edit_task=${task.id}" class="cp-btn" style="margin-top:8px;">Düzenle / kaynak ekle</a>`;

    const phaseLabel = phase ? `Faz ${phase.order + 1} — ${phase.theme}` : "";
    const phaseRange = phase ? formatDateRange(phase.start_date, phase.due_date) : "";
    content.innerHTML =
      `<h2>${escapeHtml(task.title)}</h2>` +
      `<div class="modal-meta"><span style="color:${catColor};">● ${escapeHtml(cat ? cat.name : "")}</span> · ${escapeHtml(phaseLabel)} · ${escapeHtml(phaseRange)}` +
      ((task.weight || 0) >= 5 ? ' · <span style="color:#e07878;">yüksek öncelik</span>' : "") +
      "</div>" +
      (task.description
        ? `<section><h3>Açıklama</h3><p>${escapeHtml(task.description)}</p></section>`
        : "") +
      ddHTML +
      resourcesHTML +
      aiHTML +
      editBtn;
    document.getElementById("modal-overlay").classList.add("active");
  }

  function openTaskCreate(phaseId, categoryId) {
    window.location.href = `/career/manage/?new_task=1&phase=${phaseId}&category=${categoryId}`;
  }

  function closeModal() {
    document.getElementById("modal-overlay").classList.remove("active");
  }

  function applyFilters() {
    document.querySelectorAll(".task-chip").forEach((chip) => {
      const id = parseInt(chip.dataset.taskId, 10);
      const task = tasks.find((t) => t.id === id);
      if (!task) return;
      const cat = categories.find((c) => c.id === task.category);
      let show = true;
      if (currentCat !== "all" && (!cat || cat.key !== currentCat)) show = false;
      if (currentType !== "all" && task.type !== currentType) show = false;
      if (currentSearch) {
        const hay = (task.title + " " + (task.description || "")).toLowerCase();
        if (!hay.includes(currentSearch.toLowerCase())) show = false;
      }
      chip.style.display = show ? "" : "none";
    });
    document.querySelectorAll(".matrix-cell:not(.header-cell):not(.row-header)").forEach((cell) => {
      const cat = cell.dataset.cat;
      if (currentCat !== "all" && cat && cat !== currentCat) cell.classList.add("dimmed");
      else cell.classList.remove("dimmed");
    });
    document.querySelectorAll(".row-header").forEach((rh) => {
      const isMatch = currentCat === "all" || rh.dataset.cat === currentCat;
      rh.style.opacity = isMatch ? "1" : "0.3";
    });
  }

  function updateStats() {
    const done = tasks.filter((t) => t.completed).length;
    document.getElementById("stat-total").textContent = tasks.length;
    document.getElementById("stat-done").textContent = done;
    document.getElementById("stat-pct").textContent = tasks.length
      ? Math.round((done / tasks.length) * 100) + "%"
      : "0%";
  }

  function formatDate(iso) {
    if (!iso) return "";
    const d = new Date(iso + "T00:00:00");
    if (isNaN(d.getTime())) return iso;
    const months = ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"];
    return `${months[d.getMonth()]} ${d.getFullYear()}`;
  }

  function formatDateRange(start, end) {
    const a = formatDate(start);
    const b = formatDate(end);
    if (!a && !b) return "tarih yok";
    if (a && b) return `${a} → ${b}`;
    return a || b;
  }

  function escapeHtml(s) {
    if (s == null) return "";
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function bindGlobalEvents() {
    document.getElementById("modal-close").addEventListener("click", closeModal);
    document.getElementById("modal-overlay").addEventListener("click", (e) => {
      if (e.target.id === "modal-overlay") closeModal();
    });
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") closeModal();
    });

    document.querySelectorAll(".filter-btn[data-cat='all']").forEach((btn) => {
      btn.addEventListener("click", () => {
        document.querySelectorAll(".filter-btn[data-cat]").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        currentCat = "all";
        applyFilters();
      });
    });
    document.querySelectorAll(".filter-btn[data-type]").forEach((btn) => {
      btn.addEventListener("click", () => {
        document.querySelectorAll(".filter-btn[data-type]").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        currentType = btn.dataset.type;
        applyFilters();
      });
    });
    document.getElementById("search").addEventListener("input", (e) => {
      currentSearch = e.target.value;
      applyFilters();
    });
  }

  async function init() {
    try {
      await loadAll();
      renderCategoryFilters();
      renderLegend();
      renderDeepDiveNav();
      renderMatrix();
      bindGlobalEvents();
      updateStats();
      applyFilters();
    } catch (err) {
      console.error("CareerPath init failed:", err);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
