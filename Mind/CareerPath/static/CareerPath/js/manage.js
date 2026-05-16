(function () {
  "use strict";

  const API = "/career/api/";

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

  function unwrap(d) {
    return Array.isArray(d) ? d : d.results || [];
  }

  const state = {
    phases: [],
    categories: [],
    tasks: [],
    deepDives: [],
  };

  async function refresh() {
    const [p, c, t, d] = await Promise.all([
      api(API + "phases/"),
      api(API + "categories/"),
      api(API + "tasks/"),
      api(API + "deep-dives/"),
    ]);
    state.phases = unwrap(p);
    state.categories = unwrap(c);
    state.tasks = unwrap(t);
    state.deepDives = unwrap(d);
    renderAll();
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

  // ----- TAB SWITCHING -----
  function setTab(name) {
    document.querySelectorAll(".nav-item[data-tab]").forEach((b) => {
      b.classList.toggle("active", b.dataset.tab === name);
    });
    document.querySelectorAll("[data-pane]").forEach((s) => {
      s.hidden = s.dataset.pane !== name;
    });
  }

  // ----- MODAL -----
  const modalOverlay = document.getElementById("cp-modal-overlay");
  const modalContent = document.getElementById("cp-modal-content");

  function openModal(html) {
    modalContent.innerHTML = html;
    modalOverlay.classList.add("active");
  }
  function closeModal() {
    modalOverlay.classList.remove("active");
    modalContent.innerHTML = "";
  }
  document.getElementById("cp-modal-close").addEventListener("click", closeModal);
  modalOverlay.addEventListener("click", (e) => {
    if (e.target === modalOverlay) closeModal();
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeModal();
  });

  function input(label, name, value, type = "text", extra = "") {
    return `<div class="cp-form-row"><label>${label}</label><input class="cp-input" name="${name}" type="${type}" value="${escapeHtml(value || "")}" ${extra}></div>`;
  }
  function textarea(label, name, value, rows = 4) {
    return `<div class="cp-form-row"><label>${label}</label><textarea class="cp-textarea" name="${name}" rows="${rows}">${escapeHtml(value || "")}</textarea></div>`;
  }
  function select(label, name, options, value) {
    const opts = options
      .map(
        (o) =>
          `<option value="${escapeHtml(o.value)}" ${String(o.value) === String(value || "") ? "selected" : ""}>${escapeHtml(o.label)}</option>`
      )
      .join("");
    return `<div class="cp-form-row"><label>${label}</label><select class="cp-select" name="${name}">${opts}</select></div>`;
  }

  function formActions(submitLabel = "Kaydet") {
    return `<div class="form-actions"><button type="button" class="cp-btn" data-cancel>İptal</button><button type="submit" class="cp-btn cp-btn-primary">${submitLabel}</button></div><div class="form-error" data-error hidden></div>`;
  }

  function readForm(form) {
    const data = {};
    new FormData(form).forEach((v, k) => {
      data[k] = v;
    });
    return data;
  }

  function showFormError(form, err) {
    const e = form.querySelector("[data-error]");
    e.textContent = String(err && err.message ? err.message : err);
    e.hidden = false;
  }

  // ----- PHASES -----
  function renderPhases() {
    const list = document.getElementById("phase-list");
    if (!state.phases.length) {
      list.innerHTML = '<div class="empty-cell">Henüz faz yok.</div>';
      return;
    }
    list.innerHTML = state.phases
      .map(
        (p) => `
      <div class="cp-list-item">
        <div class="info">
          <div class="info-title">Faz ${p.order + 1} — ${escapeHtml(p.theme)}</div>
          <div class="info-meta">${escapeHtml(formatDateRange(p.start_date, p.due_date))} · sıra ${p.order}</div>
        </div>
        <div class="actions">
          <button class="icon-btn" data-edit-phase="${p.id}">Düzenle</button>
          <button class="icon-btn danger" data-del-phase="${p.id}">Sil</button>
        </div>
      </div>`
      )
      .join("");
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

  function suggestNextOrder() {
    const used = new Set(state.phases.map((p) => p.order));
    let n = 0;
    while (used.has(n)) n++;
    return n;
  }

  function openPhaseForm(phase = null) {
    const p = phase || {};
    const orderVal = phase ? p.order : suggestNextOrder();
    openModal(`
      <h2>${phase ? "Faz düzenle" : "Yeni faz"}</h2>
      <form class="cp-form" id="phase-form">
        ${input("Tema (örn Temel atma)", "theme", p.theme)}
        ${input("Başlangıç tarihi", "start_date", p.start_date || "", "date")}
        ${input("Bitiş tarihi", "due_date", p.due_date || "", "date")}
        ${input("Sıra (her faz farklı bir değer almalı)", "order", orderVal, "number", "min=0")}
        ${formActions()}
      </form>`);
    const form = document.getElementById("phase-form");
    form.querySelector("[data-cancel]").addEventListener("click", closeModal);
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      try {
        const body = readForm(form);
        body.order = parseInt(body.order || "0", 10);
        body.start_date = body.start_date || null;
        body.due_date = body.due_date || null;
        const url = phase ? `${API}phases/${phase.id}/` : `${API}phases/`;
        await api(url, { method: phase ? "PUT" : "POST", body: JSON.stringify(body) });
        closeModal();
        await refresh();
      } catch (err) {
        showFormError(form, err);
      }
    });
  }

  async function delPhase(id) {
    if (!confirm("Bu fazı (ve içindeki görevleri) silmek istediğine emin misin?")) return;
    await api(`${API}phases/${id}/`, { method: "DELETE" });
    await refresh();
  }

  // ----- CATEGORIES -----
  function renderCategories() {
    const list = document.getElementById("category-list");
    if (!state.categories.length) {
      list.innerHTML = '<div class="empty-cell">Henüz kategori yok.</div>';
      return;
    }
    list.innerHTML = state.categories
      .map(
        (c) => `
      <div class="cp-list-item">
        <div class="info">
          <div class="info-title">${escapeHtml(c.name)}
            <span style="display:inline-block;width:10px;height:10px;border-radius:2px;background:${escapeHtml(resolveColor(c.color))};margin-left:8px;vertical-align:middle;"></span>
          </div>
          <div class="info-meta">anahtar: <code>${escapeHtml(c.key)}</code> · renk: <code>${escapeHtml(c.color)}</code> · sıra ${c.order}</div>
        </div>
        <div class="actions">
          <button class="icon-btn" data-edit-cat="${c.id}">Düzenle</button>
          <button class="icon-btn danger" data-del-cat="${c.id}">Sil</button>
        </div>
      </div>`
      )
      .join("");
  }

  function resolveColor(token) {
    if (!token) return "var(--text-muted)";
    if (token.startsWith("--")) return `var(${token})`;
    if (token.startsWith("var(") || token.startsWith("#") || token.startsWith("rgb")) return token;
    return `var(--accent-${token})`;
  }

  function suggestNextCategoryOrder() {
    const used = new Set(state.categories.map((c) => c.order));
    let n = 0;
    while (used.has(n)) n++;
    return n;
  }

  function openCategoryForm(cat = null) {
    const c = cat || {};
    const orderVal = cat ? c.order : suggestNextCategoryOrder();
    openModal(`
      <h2>${cat ? "Kategori düzenle" : "Yeni kategori"}</h2>
      <form class="cp-form" id="cat-form">
        ${input("Anahtar (örn arch)", "key", c.key)}
        ${input("İsim (örn Sistem mimarisi)", "name", c.name)}
        ${input("Renk (örn #8b7fd4 veya arch)", "color", c.color)}
        ${input("Sıra (her kategori farklı bir değer almalı)", "order", orderVal, "number", "min=0")}
        ${formActions()}
      </form>
      <p style="font-size:11px;color:var(--text-muted);margin-top:8px;">İpucu: renk için palet anahtarları — <code>arch, ai, eng, vis, net, visa</code> — ya da herhangi bir CSS rengi.</p>`);
    const form = document.getElementById("cat-form");
    form.querySelector("[data-cancel]").addEventListener("click", closeModal);
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      try {
        const body = readForm(form);
        body.order = parseInt(body.order || "0", 10);
        const url = cat ? `${API}categories/${cat.id}/` : `${API}categories/`;
        await api(url, { method: cat ? "PUT" : "POST", body: JSON.stringify(body) });
        closeModal();
        await refresh();
      } catch (err) {
        showFormError(form, err);
      }
    });
  }

  async function delCategory(id) {
    if (!confirm("Bu kategoriyi (ve içindeki görevleri) silmek istediğine emin misin?")) return;
    await api(`${API}categories/${id}/`, { method: "DELETE" });
    await refresh();
  }

  // ----- TASKS -----
  function renderTasks() {
    const list = document.getElementById("task-list");
    if (!state.tasks.length) {
      list.innerHTML = '<div class="empty-cell">Henüz görev yok.</div>';
      return;
    }
    list.innerHTML = state.tasks
      .map((t) => {
        const ph = state.phases.find((p) => p.id === t.phase);
        const cat = state.categories.find((c) => c.id === t.category);
        const dd = t.deep_dive ? state.deepDives.find((d) => d.id === t.deep_dive) : null;
        return `
      <div class="cp-list-item">
        <div class="info">
          <div class="info-title">${escapeHtml(t.title)} ${t.completed ? "<span class=\"badge\" style=\"color:var(--accent-ai)\">✓</span>" : ""}</div>
          <div class="info-meta">
            ${ph ? "Faz " + (ph.order + 1) : "?"} ·
            ${cat ? escapeHtml(cat.name) : "?"} ·
            tip: ${escapeHtml(t.type || "—")} · ağırlık ${t.weight}
            ${dd ? " · deep: " + escapeHtml(dd.slug) : ""}
            · ${t.resources ? t.resources.length : 0} kaynak
          </div>
        </div>
        <div class="actions">
          <button class="icon-btn" data-edit-task="${t.id}">Düzenle</button>
          <button class="icon-btn" data-resources-task="${t.id}">Kaynaklar</button>
          <button class="icon-btn danger" data-del-task="${t.id}">Sil</button>
        </div>
      </div>`;
      })
      .join("");
  }

  function openTaskForm(task = null, prefill = {}) {
    const t = task || {};
    const phaseOpts = state.phases.map((p) => ({ value: p.id, label: `Faz ${p.order + 1} — ${p.theme}` }));
    const catOpts = state.categories.map((c) => ({ value: c.id, label: c.name }));
    const ddOpts = [{ value: "", label: "— yok —" }].concat(
      state.deepDives.map((d) => ({ value: d.id, label: d.title }))
    );
    const typeOpts = [
      { value: "", label: "Diğer" },
      { value: "book", label: "Kitap" },
      { value: "project", label: "Proje" },
      { value: "cert", label: "Sertifika" },
    ];

    openModal(`
      <h2>${task ? "Görev düzenle" : "Yeni görev"}</h2>
      <form class="cp-form" id="task-form">
        ${input("Başlık", "title", t.title)}
        ${select("Faz", "phase", phaseOpts, t.phase || prefill.phase)}
        ${select("Kategori", "category", catOpts, t.category || prefill.category)}
        ${select("Tip", "type", typeOpts, t.type || "")}
        ${select("Deep dive bağlantısı", "deep_dive", ddOpts, t.deep_dive || "")}
        ${input("Ağırlık (1-5)", "weight", t.weight || 1, "number", "min=1 max=5")}
        ${input("Sıra", "order", t.order || 0, "number")}
        ${textarea("Açıklama", "description", t.description, 4)}
        ${textarea("AI nasıl kullanılır", "ai_usage", t.ai_usage, 3)}
        ${formActions()}
      </form>`);
    const form = document.getElementById("task-form");
    form.querySelector("[data-cancel]").addEventListener("click", closeModal);
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      try {
        const body = readForm(form);
        body.weight = parseInt(body.weight || "1", 10);
        body.order = parseInt(body.order || "0", 10);
        body.phase = parseInt(body.phase, 10);
        body.category = parseInt(body.category, 10);
        body.deep_dive = body.deep_dive ? parseInt(body.deep_dive, 10) : null;
        const url = task ? `${API}tasks/${task.id}/` : `${API}tasks/`;
        await api(url, { method: task ? "PUT" : "POST", body: JSON.stringify(body) });
        closeModal();
        await refresh();
      } catch (err) {
        showFormError(form, err);
      }
    });
  }

  async function delTask(id) {
    if (!confirm("Bu görevi silmek istediğine emin misin?")) return;
    await api(`${API}tasks/${id}/`, { method: "DELETE" });
    await refresh();
  }

  async function openTaskResources(taskId) {
    const task = state.tasks.find((t) => t.id === taskId);
    if (!task) return;
    const resHtml = (task.resources || [])
      .map(
        (r) => `
        <div class="cp-list-item">
          <div class="info">
            <div class="info-title">${escapeHtml(r.title)}</div>
            <div class="info-meta">${escapeHtml(r.meta || "")}</div>
          </div>
          <div class="actions">
            <button class="icon-btn danger" data-del-res="${r.id}">Sil</button>
          </div>
        </div>`
      )
      .join("");
    openModal(`
      <h2>${escapeHtml(task.title)} — kaynaklar</h2>
      <div class="cp-list" id="res-list" style="margin-bottom:16px;">${resHtml || '<div class="empty-cell">Henüz kaynak yok.</div>'}</div>
      <form class="cp-form" id="res-form">
        ${input("Başlık", "title", "")}
        ${input("Meta (kısa açıklama)", "meta", "")}
        ${formActions("+ Ekle")}
      </form>`);
    const form = document.getElementById("res-form");
    form.querySelector("[data-cancel]").addEventListener("click", closeModal);
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      try {
        const body = readForm(form);
        body.task = task.id;
        await api(`${API}task-resources/`, { method: "POST", body: JSON.stringify(body) });
        await refresh();
        openTaskResources(taskId);
      } catch (err) {
        showFormError(form, err);
      }
    });
    document.getElementById("res-list").addEventListener("click", async (e) => {
      const btn = e.target.closest("[data-del-res]");
      if (!btn) return;
      const id = parseInt(btn.dataset.delRes, 10);
      if (!confirm("Bu kaynağı silmek istediğine emin misin?")) return;
      await api(`${API}task-resources/${id}/`, { method: "DELETE" });
      await refresh();
      openTaskResources(taskId);
    });
  }

  // ----- DEEP DIVES -----
  function renderDeepDives() {
    const list = document.getElementById("deepdive-list");
    if (!state.deepDives.length) {
      list.innerHTML = '<div class="empty-cell">Henüz deep dive yok.</div>';
      return;
    }
    list.innerHTML = state.deepDives
      .map(
        (d) => `
      <div class="cp-list-item">
        <div class="info">
          <div class="info-title">${escapeHtml(d.title)}</div>
          <div class="info-meta">slug: <code>${escapeHtml(d.slug)}</code> · öncelik ${escapeHtml(d.priority_display || d.priority)} · ${d.topics ? d.topics.length : 0} konu · ${d.resources ? d.resources.length : 0} kaynak</div>
        </div>
        <div class="actions">
          <a class="icon-btn" href="/career/deep/${encodeURIComponent(d.slug)}/">Görüntüle</a>
          <button class="icon-btn" data-edit-dd="${d.id}">Düzenle</button>
          <button class="icon-btn" data-topics-dd="${d.id}">Konular</button>
          <button class="icon-btn" data-resources-dd="${d.id}">Kaynaklar</button>
          <button class="icon-btn danger" data-del-dd="${d.id}">Sil</button>
        </div>
      </div>`
      )
      .join("");
  }

  function openDeepDiveForm(dd = null) {
    const d = dd || {};
    const prioOpts = [
      { value: "low", label: "Düşük" },
      { value: "medium", label: "Orta" },
      { value: "high", label: "Yüksek" },
    ];
    openModal(`
      <h2>${dd ? "Deep dive düzenle" : "Yeni deep dive"}</h2>
      <form class="cp-form" id="dd-form">
        ${input("Slug (URL anahtarı, örn ddia)", "slug", d.slug)}
        ${input("Başlık", "title", d.title)}
        ${textarea("Tagline (kısa açıklama)", "tagline", d.tagline, 3)}
        ${textarea("Overview (paragrafları boş satırla ayır)", "overview", d.overview, 5)}
        ${textarea("Strateji", "strategy", d.strategy, 4)}
        ${input("Meta etiketler (virgülle, örn ~600 sayfa, 12 bölüm)", "meta_pills", d.meta_pills)}
        ${select("Öncelik", "priority", prioOpts, d.priority || "medium")}
        ${input("Sıra", "order", d.order || 0, "number")}
        ${formActions()}
      </form>`);
    const form = document.getElementById("dd-form");
    form.querySelector("[data-cancel]").addEventListener("click", closeModal);
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      try {
        const body = readForm(form);
        body.order = parseInt(body.order || "0", 10);
        const url = dd ? `${API}deep-dives/${dd.slug}/` : `${API}deep-dives/`;
        await api(url, { method: dd ? "PUT" : "POST", body: JSON.stringify(body) });
        closeModal();
        await refresh();
      } catch (err) {
        showFormError(form, err);
      }
    });
  }

  async function delDeepDive(slug) {
    if (!confirm("Bu deep dive bölümünü (tüm konuları+kaynaklarıyla) silmek istediğine emin misin?")) return;
    await api(`${API}deep-dives/${slug}/`, { method: "DELETE" });
    await refresh();
  }

  // ----- TOPICS (deep dive içinde) -----
  async function openTopics(ddId) {
    const dd = state.deepDives.find((d) => d.id === ddId);
    if (!dd) return;
    const items = (dd.topics || [])
      .map(
        (t) => `
        <div class="cp-list-item">
          <div class="info">
            <div class="info-title">${escapeHtml(t.num)}. ${escapeHtml(t.name)}</div>
            <div class="info-meta">${escapeHtml(t.sub_title || "")} · ${t.concepts ? t.concepts.length : 0} kavram</div>
          </div>
          <div class="actions">
            <button class="icon-btn" data-edit-topic="${t.id}">Düzenle</button>
            <button class="icon-btn" data-concepts-topic="${t.id}">Kavramlar</button>
            <button class="icon-btn danger" data-del-topic="${t.id}">Sil</button>
          </div>
        </div>`
      )
      .join("");
    openModal(`
      <h2>${escapeHtml(dd.title)} — konular</h2>
      <div class="cp-list" id="topic-list" style="margin-bottom:16px;">${items || '<div class="empty-cell">Henüz konu yok.</div>'}</div>
      <button class="cp-btn cp-btn-primary" id="topic-new">+ Yeni konu</button>`);
    document.getElementById("topic-new").addEventListener("click", () => openTopicForm(dd));
    document.getElementById("topic-list").addEventListener("click", async (e) => {
      const editBtn = e.target.closest("[data-edit-topic]");
      const delBtn = e.target.closest("[data-del-topic]");
      const conceptBtn = e.target.closest("[data-concepts-topic]");
      if (editBtn) {
        const t = dd.topics.find((x) => x.id === parseInt(editBtn.dataset.editTopic, 10));
        openTopicForm(dd, t);
      } else if (delBtn) {
        if (!confirm("Bu konuyu silmek istediğine emin misin?")) return;
        await api(`${API}topics/${delBtn.dataset.delTopic}/`, { method: "DELETE" });
        await refresh();
        openTopics(ddId);
      } else if (conceptBtn) {
        const t = dd.topics.find((x) => x.id === parseInt(conceptBtn.dataset.conceptsTopic, 10));
        openConcepts(dd, t);
      }
    });
  }

  function openTopicForm(dd, topic = null) {
    const t = topic || {};
    openModal(`
      <h2>${topic ? "Konu düzenle" : "Yeni konu"} — ${escapeHtml(dd.title)}</h2>
      <form class="cp-form" id="topic-form">
        ${input("Numara (örn 01)", "num", t.num)}
        ${input("İsim", "name", t.name)}
        ${input("Alt başlık (opsiyonel)", "sub_title", t.sub_title)}
        ${textarea("Senin domain'inde", "domain_text", t.domain_text, 3)}
        ${textarea("AI nasıl kullanılır", "ai_text", t.ai_text, 3)}
        ${input("Sıra", "order", t.order || 0, "number")}
        ${formActions()}
      </form>`);
    const form = document.getElementById("topic-form");
    form.querySelector("[data-cancel]").addEventListener("click", () => openTopics(dd.id));
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      try {
        const body = readForm(form);
        body.order = parseInt(body.order || "0", 10);
        body.deep_dive = dd.id;
        const url = topic ? `${API}topics/${topic.id}/` : `${API}topics/`;
        await api(url, { method: topic ? "PUT" : "POST", body: JSON.stringify(body) });
        await refresh();
        openTopics(dd.id);
      } catch (err) {
        showFormError(form, err);
      }
    });
  }

  async function openConcepts(dd, topic) {
    // refresh dd from state in case topics changed
    const freshDD = state.deepDives.find((x) => x.id === dd.id);
    const freshTopic = freshDD.topics.find((x) => x.id === topic.id);
    const items = (freshTopic.concepts || [])
      .map(
        (c) =>
          `<div class="cp-list-item"><div class="info"><div class="info-title">${escapeHtml(c.text)}</div></div><div class="actions"><button class="icon-btn danger" data-del-concept="${c.id}">Sil</button></div></div>`
      )
      .join("");
    openModal(`
      <h2>${escapeHtml(freshTopic.num)}. ${escapeHtml(freshTopic.name)} — kavramlar</h2>
      <div class="cp-list" id="concept-list" style="margin-bottom:16px;">${items || '<div class="empty-cell">Henüz kavram yok.</div>'}</div>
      <form class="cp-form" id="concept-form">
        ${input("Yeni kavram", "text", "")}
        ${formActions("+ Ekle")}
      </form>`);
    const form = document.getElementById("concept-form");
    form.querySelector("[data-cancel]").addEventListener("click", () => openTopics(dd.id));
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      try {
        const body = readForm(form);
        body.topic = freshTopic.id;
        await api(`${API}concepts/`, { method: "POST", body: JSON.stringify(body) });
        await refresh();
        openConcepts(state.deepDives.find((x) => x.id === dd.id), freshTopic);
      } catch (err) {
        showFormError(form, err);
      }
    });
    document.getElementById("concept-list").addEventListener("click", async (e) => {
      const btn = e.target.closest("[data-del-concept]");
      if (!btn) return;
      if (!confirm("Bu kavramı silmek istediğine emin misin?")) return;
      await api(`${API}concepts/${btn.dataset.delConcept}/`, { method: "DELETE" });
      await refresh();
      openConcepts(state.deepDives.find((x) => x.id === dd.id), freshTopic);
    });
  }

  // ----- DEEP DIVE RESOURCES -----
  async function openDDResources(ddId) {
    const dd = state.deepDives.find((d) => d.id === ddId);
    if (!dd) return;
    const items = (dd.resources || [])
      .map(
        (r) => `
        <div class="cp-list-item">
          <div class="info">
            <div class="info-title">${escapeHtml(r.title)}</div>
            <div class="info-meta">${escapeHtml(r.res_type)}${r.meta ? " · " + escapeHtml(r.meta) : ""}${r.link ? " · " + escapeHtml(r.link) : ""}</div>
          </div>
          <div class="actions">
            <button class="icon-btn danger" data-del-ddres="${r.id}">Sil</button>
          </div>
        </div>`
      )
      .join("");
    openModal(`
      <h2>${escapeHtml(dd.title)} — kaynaklar</h2>
      <div class="cp-list" id="ddres-list" style="margin-bottom:16px;">${items || '<div class="empty-cell">Henüz kaynak yok.</div>'}</div>
      <form class="cp-form" id="ddres-form">
        ${input("Tür (örn Ana kitap)", "res_type", "")}
        ${input("Başlık", "title", "")}
        ${input("Meta", "meta", "")}
        ${input("Link (opsiyonel)", "link", "")}
        ${formActions("+ Ekle")}
      </form>`);
    const form = document.getElementById("ddres-form");
    form.querySelector("[data-cancel]").addEventListener("click", closeModal);
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      try {
        const body = readForm(form);
        body.deep_dive = dd.id;
        await api(`${API}deep-dive-resources/`, { method: "POST", body: JSON.stringify(body) });
        await refresh();
        openDDResources(ddId);
      } catch (err) {
        showFormError(form, err);
      }
    });
    document.getElementById("ddres-list").addEventListener("click", async (e) => {
      const btn = e.target.closest("[data-del-ddres]");
      if (!btn) return;
      if (!confirm("Bu kaynağı silmek istediğine emin misin?")) return;
      await api(`${API}deep-dive-resources/${btn.dataset.delDdres}/`, { method: "DELETE" });
      await refresh();
      openDDResources(ddId);
    });
  }

  // ----- DISPATCH -----
  function renderAll() {
    renderPhases();
    renderCategories();
    renderTasks();
    renderDeepDives();
  }

  function bindEvents() {
    document.querySelectorAll(".nav-item[data-tab]").forEach((b) => {
      b.addEventListener("click", () => setTab(b.dataset.tab));
    });
    document.body.addEventListener("click", (e) => {
      const a = e.target.dataset.action;
      if (a === "new-phase") return openPhaseForm();
      if (a === "new-category") return openCategoryForm();
      if (a === "new-task") return openTaskForm();
      if (a === "new-deepdive") return openDeepDiveForm();

      const ep = e.target.closest("[data-edit-phase]");
      const dp = e.target.closest("[data-del-phase]");
      const ec = e.target.closest("[data-edit-cat]");
      const dc = e.target.closest("[data-del-cat]");
      const et = e.target.closest("[data-edit-task]");
      const dt = e.target.closest("[data-del-task]");
      const rt = e.target.closest("[data-resources-task]");
      const edd = e.target.closest("[data-edit-dd]");
      const ddd = e.target.closest("[data-del-dd]");
      const tdd = e.target.closest("[data-topics-dd]");
      const rdd = e.target.closest("[data-resources-dd]");

      if (ep) return openPhaseForm(state.phases.find((p) => p.id === parseInt(ep.dataset.editPhase, 10)));
      if (dp) return delPhase(parseInt(dp.dataset.delPhase, 10));
      if (ec) return openCategoryForm(state.categories.find((c) => c.id === parseInt(ec.dataset.editCat, 10)));
      if (dc) return delCategory(parseInt(dc.dataset.delCat, 10));
      if (et) return openTaskForm(state.tasks.find((t) => t.id === parseInt(et.dataset.editTask, 10)));
      if (dt) return delTask(parseInt(dt.dataset.delTask, 10));
      if (rt) return openTaskResources(parseInt(rt.dataset.resourcesTask, 10));
      if (edd) return openDeepDiveForm(state.deepDives.find((d) => d.id === parseInt(edd.dataset.editDd, 10)));
      if (ddd) {
        const d = state.deepDives.find((x) => x.id === parseInt(ddd.dataset.delDd, 10));
        if (d) delDeepDive(d.slug);
        return;
      }
      if (tdd) return openTopics(parseInt(tdd.dataset.topicsDd, 10));
      if (rdd) return openDDResources(parseInt(rdd.dataset.resourcesDd, 10));
    });
  }

  function handleQueryActions() {
    const params = new URLSearchParams(window.location.search);
    if (params.get("new_task") === "1") {
      const phase = params.get("phase");
      const category = params.get("category");
      setTab("tasks");
      openTaskForm(null, { phase, category });
    } else if (params.get("edit_task")) {
      const id = parseInt(params.get("edit_task"), 10);
      const t = state.tasks.find((x) => x.id === id);
      if (t) {
        setTab("tasks");
        openTaskForm(t);
      }
    } else if (params.get("edit_dd")) {
      const id = parseInt(params.get("edit_dd"), 10);
      const d = state.deepDives.find((x) => x.id === id);
      if (d) {
        setTab("deepdives");
        openDeepDiveForm(d);
      }
    }
  }

  async function init() {
    bindEvents();
    try {
      await refresh();
      handleQueryActions();
    } catch (err) {
      console.error("manage init failed:", err);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
