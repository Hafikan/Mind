(function () {
  "use strict";

  const API = "/notebook/api/";

  // ----- HELPERS -----
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

  function escapeHtml(s) {
    if (s == null) return "";
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function debounce(fn, ms) {
    let t;
    return function (...args) {
      clearTimeout(t);
      t = setTimeout(() => fn.apply(this, args), ms);
    };
  }

  // ----- STATE -----
  const state = {
    tree: null, // root node
    notes: [], // flat
    tags: [], // {id, name, note_count}
    activeNoteId: null,
    activeNote: null,
    knownTitles: new Set(),
    saving: false,
    pendingChange: false,
  };

  // ----- TREE RENDER -----
  async function refreshTree() {
    const tree = await api(API + "folders/tree/");
    state.tree = tree;
    state.notes = [];
    collectNotes(tree, state.notes);
    state.knownTitles = new Set(state.notes.map((n) => n.title.toLowerCase()));
    renderTree();
  }

  function collectNotes(node, out) {
    (node.notes || []).forEach((n) => out.push(n));
    (node.children || []).forEach((c) => collectNotes(c, out));
  }

  function renderTree() {
    const root = document.getElementById("nb-tree");
    root.innerHTML = "";
    root.appendChild(buildFolderNode(state.tree, true));
  }

  function buildFolderNode(node, isRoot) {
    const wrap = document.createElement("div");
    wrap.className = "nb-tree-node";

    if (!isRoot) {
      const header = document.createElement("div");
      header.className = "nb-tree-folder";
      header.dataset.folderId = node.id;
      header.innerHTML = `
        <span class="nb-tree-chevron">▾</span>
        <span class="nb-tree-name">${escapeHtml(node.name)}</span>
        <span class="nb-tree-actions">
          <button class="nb-tree-mini-btn" data-action="new-note" title="Yeni not">+</button>
          <button class="nb-tree-mini-btn" data-action="rename-folder" title="Yeniden adlandır">✎</button>
          <button class="nb-tree-mini-btn" data-action="delete-folder" title="Sil">×</button>
        </span>`;
      const children = document.createElement("div");
      children.className = "nb-tree-children";

      header.addEventListener("click", (e) => {
        const action = e.target.dataset && e.target.dataset.action;
        if (action) {
          e.stopPropagation();
          if (action === "new-note") openNewNoteModal(node.id);
          if (action === "rename-folder") openRenameFolderModal(node);
          if (action === "delete-folder") deleteFolder(node);
          return;
        }
        children.classList.toggle("collapsed");
        header.querySelector(".nb-tree-chevron").textContent = children.classList.contains("collapsed") ? "▸" : "▾";
      });

      (node.children || []).forEach((c) => children.appendChild(buildFolderNode(c)));
      (node.notes || []).forEach((n) => children.appendChild(buildNoteItem(n)));

      wrap.appendChild(header);
      wrap.appendChild(children);
    } else {
      // root: render children + notes directly
      (node.children || []).forEach((c) => wrap.appendChild(buildFolderNode(c)));
      (node.notes || []).forEach((n) => wrap.appendChild(buildNoteItem(n)));
    }
    return wrap;
  }

  function buildNoteItem(note) {
    const el = document.createElement("div");
    el.className = "nb-tree-note";
    el.dataset.noteId = note.id;
    el.textContent = note.title || "(başlıksız)";
    if (state.activeNoteId === note.id) el.classList.add("active");
    el.addEventListener("click", () => loadNote(note.id));
    return el;
  }

  // ----- TAGS RENDER -----
  async function refreshTags() {
    const data = await api(API + "tags/");
    state.tags = unwrap(data);
    renderTags();
  }

  function renderTags() {
    const root = document.getElementById("nb-tags");
    root.innerHTML = "";
    if (!state.tags.length) {
      root.innerHTML = '<div style="font-size: 11px; color: var(--text-dim); padding: 6px;">Henüz etiket yok</div>';
      return;
    }
    state.tags.forEach((t) => {
      const el = document.createElement("div");
      el.className = "nb-tag";
      el.innerHTML = `#${escapeHtml(t.name)}<span class="nb-tag-count">${t.note_count || 0}</span>`;
      el.addEventListener("click", () => filterByTag(t.name));
      root.appendChild(el);
    });
  }

  async function filterByTag(name) {
    try {
      const notes = unwrap(await api(API + `notes/?tag=${encodeURIComponent(name)}`));
      const root = document.getElementById("nb-tree");
      root.innerHTML = `<div style="font-size:11px;color:var(--text-muted);margin-bottom:8px;padding:0 6px;">#${escapeHtml(name)} — <a href="#" id="nb-clear-tag" style="color:var(--accent);text-decoration:none;">temizle</a></div>`;
      notes.forEach((n) => root.appendChild(buildNoteItem({ id: n.id, title: n.title })));
      document.getElementById("nb-clear-tag").addEventListener("click", (e) => {
        e.preventDefault();
        renderTree();
      });
    } catch (err) {
      console.error(err);
    }
  }

  // ----- NOTE LOAD / RENDER -----
  async function loadNote(id) {
    try {
      const note = await api(API + `notes/${id}/`);
      state.activeNote = note;
      state.activeNoteId = id;
      document.getElementById("nb-welcome").hidden = true;
      const wrap = document.getElementById("nb-editor-wrap");
      wrap.hidden = false;
      document.getElementById("nb-title").value = note.title || "";
      document.getElementById("nb-content").value = note.content || "";
      renderPreview();
      renderBacklinks();
      markSaved();
      // Update active highlighting
      document.querySelectorAll(".nb-tree-note").forEach((el) => {
        el.classList.toggle("active", parseInt(el.dataset.noteId, 10) === id);
      });
      // Update URL without reload
      window.history.replaceState(null, "", `/notebook/n/${id}/`);
    } catch (err) {
      console.error("loadNote:", err);
    }
  }

  function renderBacklinks() {
    const note = state.activeNote;
    const wrap = document.getElementById("nb-backlinks");
    const list = document.getElementById("nb-backlinks-list");
    if (!note || !note.backlinks || !note.backlinks.length) {
      wrap.hidden = true;
      return;
    }
    wrap.hidden = false;
    list.innerHTML = note.backlinks
      .map(
        (b) =>
          `<a class="nb-backlink-item" data-note-id="${b.id}">${escapeHtml(b.title)}</a>`
      )
      .join("");
    list.querySelectorAll(".nb-backlink-item").forEach((el) => {
      el.addEventListener("click", () => loadNote(parseInt(el.dataset.noteId, 10)));
    });
  }

  // ----- PREVIEW RENDER -----
  function renderPreview() {
    const md = document.getElementById("nb-content").value;
    const preprocessed = preprocessMarkdown(md);
    const html = window.marked ? window.marked.parse(preprocessed) : escapeHtml(preprocessed);
    const safe = window.DOMPurify ? window.DOMPurify.sanitize(html, { ADD_ATTR: ["data-target", "data-tag"] }) : html;
    const preview = document.getElementById("nb-preview");
    preview.innerHTML = safe;
    preview.querySelectorAll(".wikilink").forEach((a) => {
      a.addEventListener("click", (e) => {
        e.preventDefault();
        followWikiLink(a.dataset.target);
      });
    });
    preview.querySelectorAll(".hashtag").forEach((a) => {
      a.addEventListener("click", (e) => {
        e.preventDefault();
        filterByTag(a.dataset.tag);
      });
    });
  }

  function preprocessMarkdown(md) {
    if (!md) return "";
    // [[wiki-link|label]] or [[wiki-link]]
    md = md.replace(/\[\[([^\]|#]+?)(?:\|([^\]]+))?\]\]/g, (_, target, label) => {
      const t = target.trim();
      const display = (label && label.trim()) || t;
      const known = state.knownTitles.has(t.toLowerCase());
      const cls = "wikilink" + (known ? "" : " broken");
      return `<a class="${cls}" data-target="${escapeHtml(t)}" href="javascript:void(0)">${escapeHtml(display)}</a>`;
    });
    // #tag — but not at start of heading line (skip if line starts with #)
    md = md.replace(/(^|[^\w\/])#([\w-]+)/g, (_match, pre, name) => {
      return `${pre}<span class="hashtag" data-tag="${escapeHtml(name)}">#${escapeHtml(name)}</span>`;
    });
    return md;
  }

  async function followWikiLink(target) {
    try {
      const res = await api(API + `notes/resolve/?title=${encodeURIComponent(target)}`);
      if (res.exists) {
        loadNote(res.id);
      } else {
        if (confirm(`"${target}" başlıklı not yok. Oluşturulsun mu?`)) {
          const created = await api(API + "notes/", {
            method: "POST",
            body: JSON.stringify({ title: target, content: "" }),
          });
          await refreshTree();
          await refreshTags();
          loadNote(created.id);
        }
      }
    } catch (err) {
      console.error(err);
    }
  }

  // ----- AUTOSAVE -----
  const saveIndicator = () => document.getElementById("nb-save-indicator");
  function markDirty() {
    state.pendingChange = true;
    const el = saveIndicator();
    el.textContent = "değişiklik var";
    el.className = "nb-save-indicator";
  }
  function markSaving() {
    const el = saveIndicator();
    el.textContent = "kaydediliyor...";
    el.className = "nb-save-indicator saving";
  }
  function markSaved() {
    state.pendingChange = false;
    const el = saveIndicator();
    el.textContent = "kaydedildi";
    el.className = "nb-save-indicator saved";
  }
  function markError(msg) {
    const el = saveIndicator();
    el.textContent = "hata!";
    el.className = "nb-save-indicator error";
    el.title = msg || "";
  }

  async function saveNow() {
    if (!state.activeNoteId || !state.pendingChange) return;
    const title = document.getElementById("nb-title").value.trim();
    const content = document.getElementById("nb-content").value;
    if (!title) return; // skip empty title save
    markSaving();
    try {
      const updated = await api(API + `notes/${state.activeNoteId}/`, {
        method: "PATCH",
        body: JSON.stringify({ title, content }),
      });
      const oldTitle = state.activeNote ? state.activeNote.title : null;
      state.activeNote = updated;
      markSaved();
      if (oldTitle !== updated.title) {
        await refreshTree();
        // restore active highlight
        document.querySelectorAll(".nb-tree-note").forEach((el) => {
          el.classList.toggle("active", parseInt(el.dataset.noteId, 10) === state.activeNoteId);
        });
      }
      await refreshTags();
      renderBacklinks();
    } catch (err) {
      console.error("save:", err);
      markError(err.message);
    }
  }

  const debouncedSave = debounce(saveNow, 800);

  // ----- DELETE NOTE -----
  async function deleteNote() {
    if (!state.activeNoteId) return;
    if (!confirm("Bu notu silmek istediğine emin misin?")) return;
    try {
      await api(API + `notes/${state.activeNoteId}/`, { method: "DELETE" });
      state.activeNoteId = null;
      state.activeNote = null;
      document.getElementById("nb-editor-wrap").hidden = true;
      document.getElementById("nb-welcome").hidden = false;
      window.history.replaceState(null, "", "/notebook/");
      await refreshTree();
      await refreshTags();
    } catch (err) {
      console.error(err);
    }
  }

  // ----- MODALS -----
  const modalOverlay = () => document.getElementById("nb-modal-overlay");
  function openModal(html) {
    document.getElementById("nb-modal-content").innerHTML = html;
    modalOverlay().classList.add("active");
  }
  function closeModal() {
    modalOverlay().classList.remove("active");
    document.getElementById("nb-modal-content").innerHTML = "";
  }
  document.getElementById("nb-modal-close").addEventListener("click", closeModal);
  modalOverlay().addEventListener("click", (e) => {
    if (e.target === modalOverlay()) closeModal();
  });

  function folderOptionsHtml(selectedId) {
    const flat = [];
    function walk(node, depth) {
      if (node.id != null) flat.push({ id: node.id, label: "—".repeat(depth) + " " + node.name });
      (node.children || []).forEach((c) => walk(c, depth + 1));
    }
    walk(state.tree, 0);
    return (
      '<option value="">(kök)</option>' +
      flat
        .map(
          (f) => `<option value="${f.id}" ${String(f.id) === String(selectedId || "") ? "selected" : ""}>${escapeHtml(f.label)}</option>`
        )
        .join("")
    );
  }

  function openNewNoteModal(folderId = null) {
    openModal(`
      <h2>Yeni not</h2>
      <form class="nb-modal-form" id="nb-new-note-form">
        <div>
          <label>Başlık</label>
          <input class="nb-input" name="title" required autofocus>
        </div>
        <div>
          <label>Klasör</label>
          <select name="folder">${folderOptionsHtml(folderId)}</select>
        </div>
        <div class="nb-form-error" id="nb-form-error" hidden></div>
        <div class="nb-modal-actions">
          <button type="button" class="nb-btn" id="nb-cancel">İptal</button>
          <button type="submit" class="nb-btn nb-btn-primary">Oluştur</button>
        </div>
      </form>`);
    document.getElementById("nb-cancel").addEventListener("click", closeModal);
    document.getElementById("nb-new-note-form").addEventListener("submit", async (e) => {
      e.preventDefault();
      const fd = new FormData(e.target);
      const body = {
        title: fd.get("title"),
        folder: fd.get("folder") ? parseInt(fd.get("folder"), 10) : null,
        content: "",
      };
      try {
        const created = await api(API + "notes/", { method: "POST", body: JSON.stringify(body) });
        closeModal();
        await refreshTree();
        loadNote(created.id);
      } catch (err) {
        const e2 = document.getElementById("nb-form-error");
        e2.textContent = err.message;
        e2.hidden = false;
      }
    });
  }

  function openNewFolderModal() {
    openModal(`
      <h2>Yeni klasör</h2>
      <form class="nb-modal-form" id="nb-new-folder-form">
        <div>
          <label>İsim</label>
          <input class="nb-input" name="name" required autofocus>
        </div>
        <div>
          <label>Üst klasör</label>
          <select name="parent">${folderOptionsHtml(null)}</select>
        </div>
        <div class="nb-form-error" id="nb-form-error" hidden></div>
        <div class="nb-modal-actions">
          <button type="button" class="nb-btn" id="nb-cancel">İptal</button>
          <button type="submit" class="nb-btn nb-btn-primary">Oluştur</button>
        </div>
      </form>`);
    document.getElementById("nb-cancel").addEventListener("click", closeModal);
    document.getElementById("nb-new-folder-form").addEventListener("submit", async (e) => {
      e.preventDefault();
      const fd = new FormData(e.target);
      const body = {
        name: fd.get("name"),
        parent: fd.get("parent") ? parseInt(fd.get("parent"), 10) : null,
      };
      try {
        await api(API + "folders/", { method: "POST", body: JSON.stringify(body) });
        closeModal();
        await refreshTree();
      } catch (err) {
        const e2 = document.getElementById("nb-form-error");
        e2.textContent = err.message;
        e2.hidden = false;
      }
    });
  }

  function openRenameFolderModal(folder) {
    openModal(`
      <h2>Klasörü yeniden adlandır</h2>
      <form class="nb-modal-form" id="nb-rename-folder-form">
        <div>
          <label>İsim</label>
          <input class="nb-input" name="name" value="${escapeHtml(folder.name)}" required autofocus>
        </div>
        <div class="nb-form-error" id="nb-form-error" hidden></div>
        <div class="nb-modal-actions">
          <button type="button" class="nb-btn" id="nb-cancel">İptal</button>
          <button type="submit" class="nb-btn nb-btn-primary">Kaydet</button>
        </div>
      </form>`);
    document.getElementById("nb-cancel").addEventListener("click", closeModal);
    document.getElementById("nb-rename-folder-form").addEventListener("submit", async (e) => {
      e.preventDefault();
      const fd = new FormData(e.target);
      try {
        await api(API + `folders/${folder.id}/`, {
          method: "PATCH",
          body: JSON.stringify({ name: fd.get("name") }),
        });
        closeModal();
        await refreshTree();
      } catch (err) {
        const e2 = document.getElementById("nb-form-error");
        e2.textContent = err.message;
        e2.hidden = false;
      }
    });
  }

  async function deleteFolder(folder) {
    if (!confirm(`"${folder.name}" klasörünü silmek istediğine emin misin? İçindeki notlar köke taşınmaz, alt klasörler de silinir; notlar köke düşer.`)) return;
    try {
      await api(API + `folders/${folder.id}/`, { method: "DELETE" });
      await refreshTree();
    } catch (err) {
      console.error(err);
    }
  }

  // ----- SEARCH -----
  const searchInput = document.getElementById("nb-search");
  const searchResults = document.getElementById("nb-search-results");

  const debouncedSearch = debounce(async (q) => {
    if (!q.trim()) {
      searchResults.classList.remove("active");
      searchResults.innerHTML = "";
      return;
    }
    try {
      const data = await api(API + `search/?q=${encodeURIComponent(q)}`);
      if (!data.length) {
        searchResults.innerHTML = '<div class="nb-search-item"><div class="nb-search-snippet">Sonuç yok.</div></div>';
        searchResults.classList.add("active");
        return;
      }
      searchResults.innerHTML = data
        .map(
          (r) =>
            `<div class="nb-search-item" data-id="${r.id}"><div class="nb-search-title">${escapeHtml(r.title)}</div><div class="nb-search-snippet">${escapeHtml(r.snippet || "")}</div></div>`
        )
        .join("");
      searchResults.classList.add("active");
      searchResults.querySelectorAll(".nb-search-item[data-id]").forEach((el) => {
        el.addEventListener("click", () => {
          searchResults.classList.remove("active");
          searchInput.value = "";
          loadNote(parseInt(el.dataset.id, 10));
        });
      });
    } catch (err) {
      console.error(err);
    }
  }, 300);

  searchInput.addEventListener("input", (e) => debouncedSearch(e.target.value));
  document.addEventListener("click", (e) => {
    if (!searchResults.contains(e.target) && e.target !== searchInput) {
      searchResults.classList.remove("active");
    }
  });

  // ----- BINDINGS -----
  function bind() {
    document.getElementById("nb-new-note").addEventListener("click", () => openNewNoteModal());
    document.getElementById("nb-new-folder").addEventListener("click", () => openNewFolderModal());
    document.getElementById("nb-delete-note").addEventListener("click", deleteNote);

    const titleInput = document.getElementById("nb-title");
    const contentEl = document.getElementById("nb-content");
    titleInput.addEventListener("input", () => {
      markDirty();
      debouncedSave();
    });
    contentEl.addEventListener("input", () => {
      markDirty();
      renderPreview();
      debouncedSave();
    });

    // Ctrl/Cmd+S manual save
    document.addEventListener("keydown", (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "s") {
        e.preventDefault();
        saveNow();
      }
      if (e.key === "Escape") closeModal();
    });

    // Save before unload
    window.addEventListener("beforeunload", (e) => {
      if (state.pendingChange) {
        saveNow();
        e.preventDefault();
        e.returnValue = "";
      }
    });
  }

  // ----- INIT -----
  async function init() {
    bind();
    try {
      await Promise.all([refreshTree(), refreshTags()]);
      const initial = document.querySelector(".nb-root").dataset.initialNote;
      if (initial) {
        loadNote(parseInt(initial, 10));
      }
    } catch (err) {
      console.error("notebook init:", err);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
