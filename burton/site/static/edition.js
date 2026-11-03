// Reading options, notes and translation behaviour. Progressive enhancement: the text and
// Burton's notes are readable without this script.

const KEY = "burton-settings";
const root = new URL("..", import.meta.url);
const html = document.documentElement;
const body = document.body;
const wide = window.matchMedia("(min-width: 1100px)");
const DEFAULTS = { mode: "gloss", theme: "auto", size: "m", gowland: false, pages: false, order: "default", cites: false };
// Translation sources, first shown first (SPEC §6.3). Gowland's exist in the private build only.
const ORDERS = {
  default: ["editor", "djs1927", "machine", "gowland"],
  gowland: ["gowland", "editor", "djs1927", "machine"],
  machine: ["machine", "editor", "djs1927", "gowland"],
};

function load() {
  try { return JSON.parse(localStorage.getItem(KEY) || "{}"); } catch { return {}; }
}
function save(s) {
  try { localStorage.setItem(KEY, JSON.stringify(s)); return true; } catch { return false; /* private window */ }
}

const settings = Object.assign({}, DEFAULTS, load());

function apply() {
  body.classList.remove("mode-gloss", "mode-interlinear", "mode-english");
  body.classList.add(`mode-${settings.mode}`);
  if (settings.theme === "auto") delete html.dataset.theme;
  else html.dataset.theme = settings.theme;
  if (settings.size === "m") delete html.dataset.size;
  else html.dataset.size = settings.size;
  body.classList.toggle("show-gowland", !!settings.gowland);
  body.classList.toggle("show-pages", !!settings.pages);
  body.classList.toggle("show-cites", !!settings.cites);
  document.querySelectorAll(".fp.show-orig").forEach((f) => f.classList.remove("show-orig"));
  orderVersions();
  scheduleLayout();
}

// Each passage's translations, reordered to the chosen source order: the box lists them all, and
// the interlinear and English modes show the first. Without this script the build's default order stands.
function orderVersions() {
  const order = ORDERS[settings.order] || ORDERS.default;
  const rank = (v) => { const i = order.indexOf(v.dataset.src); return i < 0 ? order.length : i; };
  for (const vs of document.querySelectorAll(".ft-vs")) {
    const items = [...vs.children].sort((a, b) => rank(a) - rank(b));
    items.forEach((v) => vs.appendChild(v));
    vs.closest(".fp")?.classList.toggle("first-gowland", items[0]?.dataset.src === "gowland");
  }
}

// ---------------------------------------------------------------- reading options
function syncInputs() {
  for (const input of document.querySelectorAll(".settings input")) {
    if (input.type === "radio") input.checked = settings[input.name] === input.value;
    else input.checked = !!settings[input.name];
  }
}
for (const input of document.querySelectorAll(".settings input")) {
  input.addEventListener("change", () => {
    settings[input.name] = input.type === "radio" ? input.value : input.checked;
    const kept = save(settings);
    apply();
    const status = document.querySelector(".settings .saved");
    if (status) status.textContent = kept ? "Saved." : "Applied to this page only (this browser does not allow saving).";
  });
}
const reset = document.querySelector(".settings .reset");
if (reset) {
  reset.addEventListener("click", () => {
    Object.assign(settings, DEFAULTS);
    save(settings);
    syncInputs();
    apply();
    document.querySelector(".settings .saved").textContent = "Defaults restored.";
  });
}
syncInputs();

const panel = document.getElementById("settings");
const toggle = document.querySelector(".settings-toggle");
function setPanel(open, focusToggle) {
  panel.hidden = !open;
  toggle.setAttribute("aria-expanded", String(open));
  if (open) panel.querySelector("input:checked, input")?.focus();
  else if (focusToggle) toggle.focus();
}
if (panel && toggle) {
  toggle.addEventListener("click", () => setPanel(panel.hidden, false));
  panel.addEventListener("keydown", (ev) => {
    if (ev.key === "Escape") { ev.stopPropagation(); setPanel(false, true); }
  });
}

// ---------------------------------------------------------------- contents panel
const tocPanel = document.querySelector(".toc-panel");
if (tocPanel) {
  tocPanel.addEventListener("toggle", () => {
    if (tocPanel.open) tocPanel.querySelector('[aria-current="page"]')?.scrollIntoView({ block: "center" });
  });
  tocPanel.addEventListener("keydown", (ev) => {
    if (ev.key === "Escape" && tocPanel.open) {
      ev.stopPropagation();
      tocPanel.open = false;
      tocPanel.querySelector("summary").focus();
    }
  });
}

// ---------------------------------------------------------------- Burton's sidenotes
// Wide screens: notes sit in the right margin beside their marker. A layout pass pushes each
// note below the previous one; when a note would drift more than LIMIT below its marker, it
// and the rest of its paragraph's notes collapse into a "more notes" stack at that paragraph.
// Narrow screens (and stacked notes): the marker opens the note as a popover beside it.
const article = document.querySelector("article.unit");
const markers = [...document.querySelectorAll("a.nref")];
const canPopover = typeof HTMLElement.prototype.showPopover === "function";
const expanded = new Set(); // paragraphs whose stack the reader opened
let openNote = null;

function noteOf(marker) { return document.getElementById(marker.getAttribute("href").slice(1)); }
function blockOf(marker) { return marker.closest("p, li, .lg, blockquote, h1") || article; }

function asPopover(note, on) {
  if (!canPopover) return;
  if (on && !note.hasAttribute("popover")) note.setAttribute("popover", "auto");
  if (!on && note.hasAttribute("popover")) {
    if (note.matches(":popover-open")) note.hidePopover();
    note.removeAttribute("popover");
  }
}

function placePopover(note, marker) {
  const r = marker.getBoundingClientRect();
  const w = Math.min(352, window.innerWidth - 32);
  note.style.setProperty("--pop-w", `${w}px`);
  note.style.setProperty("--pop-x", `${Math.max(16, Math.min(r.left - 24, window.innerWidth - w - 16))}px`);
  const h = note.getBoundingClientRect().height;
  const below = r.bottom + 6 + h < window.innerHeight || r.top < h + 12;
  note.style.setProperty("--pop-y", `${below ? r.bottom + 6 : r.top - h - 6}px`);
}

function closeNote(focusMarker) {
  if (!openNote) return;
  const { note, marker } = openNote;
  openNote = null;
  if (canPopover && note.matches(":popover-open")) note.hidePopover();
  note.classList.remove("open");
  marker.setAttribute("aria-expanded", "false");
  if (focusMarker) marker.focus();
}

function openAsPopover(note, marker) {
  closeNote(false);
  openNote = { note, marker };
  marker.setAttribute("aria-expanded", "true");
  if (canPopover) {
    asPopover(note, true);
    note.showPopover();
    placePopover(note, marker);
  } else {
    note.classList.add("open"); // inline expansion fallback
  }
}

for (const marker of markers) {
  const note = noteOf(marker);
  if (!note) continue;
  marker.setAttribute("aria-controls", note.id);
  marker.setAttribute("aria-expanded", "false");
  note.addEventListener("toggle", (ev) => {
    if (ev.newState === "closed" && openNote && openNote.note === note) {
      openNote = null;
      marker.setAttribute("aria-expanded", "false");
    }
  });
  marker.addEventListener("click", (ev) => {
    ev.preventDefault();
    if (openNote && openNote.note === note) { closeNote(false); return; }
    if (wide.matches && !note.classList.contains("sn-stacked")) {
      note.classList.add("flash");
      setTimeout(() => note.classList.remove("flash"), 1200);
    } else {
      openAsPopover(note, marker);
    }
  });
}

document.addEventListener("keydown", (ev) => {
  if (ev.key !== "Escape") return;
  if (openNote) closeNote(true);
  document.querySelectorAll(".fp.pinned").forEach((f) => f.classList.remove("pinned"));
});

function layoutNotes() {
  if (!article) return;
  article.querySelectorAll(".sn-more").forEach((b) => b.remove());
  const notes = markers.map(noteOf).filter(Boolean);
  if (!wide.matches) {
    article.classList.remove("sn-laid");
    article.style.minHeight = "";
    notes.forEach((n) => { n.classList.remove("sn-stacked"); n.style.top = ""; asPopover(n, true); });
    return;
  }
  closeNote(false);
  article.classList.add("sn-laid");
  const rem = parseFloat(getComputedStyle(article).fontSize);
  const LIMIT = 14 * rem; // how far a note may drift below its marker
  const GAP = 0.4 * rem;
  const art = article.getBoundingClientRect();
  let floor = -Infinity;
  let stack = null; // {block, notes, button}
  for (const marker of markers) {
    const note = noteOf(marker);
    if (!note) continue;
    const block = blockOf(marker);
    const anchor = marker.getBoundingClientRect().top - art.top;
    const y = Math.max(anchor, floor + GAP);
    const overflow = y - anchor > LIMIT && !expanded.has(block);
    if (overflow || (stack && stack.block === block)) {
      note.classList.add("sn-stacked");
      note.style.top = "";
      asPopover(note, true);
      if (!stack || stack.block !== block) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "sn-more";
        button.setAttribute("aria-expanded", "false");
        button.style.top = `${y}px`;
        article.appendChild(button);
        button.addEventListener("click", () => { expanded.add(block); layoutNotes(); });
        stack = { block, notes: [], button };
        floor = y + button.getBoundingClientRect().height;
      }
      stack.notes.push(note);
      const n = stack.notes.length;
      stack.button.textContent = `${n} more note${n > 1 ? "s" : ""}`;
      stack.button.setAttribute("aria-label", `${n} more note${n > 1 ? "s" : ""} for this paragraph: show them in the margin`);
      continue;
    }
    stack = null;
    note.classList.remove("sn-stacked");
    asPopover(note, false);
    note.style.top = `${y}px`;
    floor = y + note.getBoundingClientRect().height;
  }
  article.style.minHeight = floor > 0 ? `${Math.ceil(floor)}px` : "";
}

let pending = 0;
function scheduleLayout() {
  if (!article) return;
  cancelAnimationFrame(pending);
  pending = requestAnimationFrame(layoutNotes);
}
if (article) {
  wide.addEventListener("change", () => { expanded.clear(); scheduleLayout(); });
  window.addEventListener("resize", scheduleLayout);
  document.fonts?.ready.then(scheduleLayout);
  window.addEventListener("load", scheduleLayout);
  new ResizeObserver(scheduleLayout).observe(article);
}

// ---------------------------------------------------------------- translations
for (const fp of document.querySelectorAll(".fp")) {
  const fid = fp.dataset.fid;
  const mine = document.querySelectorAll(`.burton-tr[data-for="${CSS.escape(fid)}"]`);
  const link = (on) => {
    fp.classList.toggle("linked", on);
    mine.forEach((s) => s.classList.toggle("linked", on));
  };
  fp.addEventListener("mouseenter", () => link(true));
  fp.addEventListener("mouseleave", () => link(false));
  fp.addEventListener("focusin", () => link(true));
  fp.addEventListener("focusout", () => link(false));
  mine.forEach((s) => {
    s.addEventListener("mouseenter", () => link(true));
    s.addEventListener("mouseleave", () => link(false));
  });
  // touch: tap pins the gloss; in English mode tap reveals the original
  fp.addEventListener("click", (ev) => {
    if (ev.target.closest("a")) return;
    if (body.classList.contains("mode-english")) fp.classList.toggle("show-orig");
    else if (body.classList.contains("mode-gloss")) fp.classList.toggle("pinned");
  });
  const ft = fp.querySelector(":scope > .ft");
  if (ft) {
    ft.tabIndex = -1;
    fp.addEventListener("keydown", (ev) => {
      if ((ev.key === "Enter" || ev.key === " ") && body.classList.contains("mode-english")) {
        ev.preventDefault();
        fp.classList.toggle("show-orig");
      }
    });
  }
}

// ---------------------------------------------------------------- synopsis tree (M7)
// The page is a fully open nested list; script adds a disclosure button to every branch, opens the branches
// above a node reached by a link (a cross-key such as ♈, or a unit's "where this stands" link) and focuses it.
const synTree = document.querySelector(".syn-tree");
if (synTree) {
  const setOpen = (li, open) => {
    const btn = li.querySelector(":scope > .syn-row > .syn-tg");
    const kids = li.querySelector(":scope > .syn-kids");
    if (!btn || !kids) return;
    btn.setAttribute("aria-expanded", String(open));
    kids.hidden = !open;
  };
  for (const li of synTree.querySelectorAll(".syn-n")) {
    const kids = li.querySelector(":scope > .syn-kids");
    if (!kids) continue;
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "syn-tg";
    btn.setAttribute("aria-expanded", "true");
    btn.setAttribute("aria-controls", kids.id);
    btn.setAttribute("aria-labelledby", li.id + "-t");
    btn.addEventListener("click", () => setOpen(li, btn.getAttribute("aria-expanded") !== "true"));
    li.querySelector(":scope > .syn-row").prepend(btn);
  }
  const reveal = () => {
    const target = location.hash && document.getElementById(decodeURIComponent(location.hash.slice(1)));
    if (!target || !synTree.contains(target)) return;
    for (let li = target.parentElement.closest(".syn-n"); li; li = li.parentElement.closest(".syn-n")) setOpen(li, true);
    target.tabIndex = -1;
    target.focus({ preventScroll: true });
    target.scrollIntoView({ block: "center" });
  };
  window.addEventListener("hashchange", reveal);
  reveal();
  const tools = document.querySelector(".syn-tools");
  if (tools) {
    tools.hidden = false;
    tools.addEventListener("click", (ev) => {
      const b = ev.target.closest("button[data-syn]");
      if (!b) return;
      for (const li of synTree.querySelectorAll(".syn-n")) setOpen(li, b.dataset.syn === "open");
    });
  }
}

apply();

// ---------------------------------------------------------------- offline (installable app)
if ("serviceWorker" in navigator && location.protocol.startsWith("http")) {
  navigator.serviceWorker.register(new URL("sw.js", root)).catch(() => {});
}
