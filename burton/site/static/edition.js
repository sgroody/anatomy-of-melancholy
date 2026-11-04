// Reading options, notes and translation behaviour. Progressive enhancement: the text and
// Burton's notes are readable without this script.

const KEY = "burton-settings";
const root = new URL("..", import.meta.url);
const html = document.documentElement;
const body = document.body;
const wide = window.matchMedia("(min-width: 1100px)");
const twoSide = window.matchMedia("(min-width: 1380px)"); // room for a margin on each side (R3)
const DEFAULTS = { mode: "gloss", theme: "auto", size: "m", gowland: false, pages: false, order: "default", cites: false, glosses: false };
// Translation sources, first shown first (SPEC §6.3). Gowland's exist in the private build only, and
// come first there (owner, 2026-11-03); "gowland" is kept as an alias for settings saved before that.
const ORDERS = {
  default: ["gowland", "editor", "djs1927", "machine"],
  gowland: ["gowland", "editor", "djs1927", "machine"],
  human: ["editor", "djs1927", "gowland", "machine"],
  machine: ["machine", "gowland", "editor", "djs1927"],
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
  body.classList.toggle("show-abbr", !!settings.cites); // "Burton's abbreviations" in place of the expansions
  body.classList.toggle("show-glosses", !!settings.glosses);
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
// Burton's markers (a.nref) and the anchors of the edition's margin items (span.mref: translations of the text,
// Gowland's notes), in reading order; each is laid out beside its anchor by the same pass.
const markers = [...document.querySelectorAll("a.nref, span.mref")];
const canPopover = typeof HTMLElement.prototype.showPopover === "function";
const expanded = new Set(); // paragraphs whose stack the reader opened
let openNote = null;

function noteOf(marker) {
  return marker.classList.contains("mref") ? document.getElementById(marker.dataset.for)
    : document.getElementById(marker.getAttribute("href").slice(1));
}
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

for (const marker of markers.filter((m) => m.matches("a.nref"))) {
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
  body.classList.toggle("mn-on", wide.matches);
  if (!wide.matches) {
    article.classList.remove("sn-laid");
    article.style.minHeight = "";
    notes.forEach((n) => { n.classList.remove("sn-stacked"); n.style.top = ""; asPopover(n, true); });
    return;
  }
  closeNote(false);
  article.classList.add("sn-laid");
  // Three passes, so the browser lays the page out once rather than once per note (M8: the longest page
  // took 1.4 s): (1) every note into the margin; (2) read every marker's place and every note's height,
  // which do not depend on each other, since laid-out notes are out of the flow; (3) place them.
  const all = markers.map((m) => [m, noteOf(m)]).filter(([, n]) => n);
  for (const [, note] of all) { note.classList.remove("sn-stacked"); asPopover(note, false); note.style.top = ""; }
  const rem = parseFloat(getComputedStyle(article).fontSize);
  const LIMIT = 14 * rem; // how far a note may drift below its marker
  const GAP = 0.4 * rem;
  const art = article.getBoundingClientRect();
  // Burton's markers and the margin anchors are interleaved by where they stand on the page, Burton's first on a tie
  const tops = new Map(all.map(([m]) => [m, m.getBoundingClientRect().top - art.top]));
  const pairs = all.map((p, i) => [p, i]).sort(([[a], i], [[b], j]) => (tops.get(a) - tops.get(b)) ||
    (a.matches("a.nref") ? 0 : 1) - (b.matches("a.nref") ? 0 : 1) || i - j).map(([p]) => p);
  // Two margins on wide windows (owner, 2026-11-03, R3): Gowland's commentary on the left, Burton's notes and the
  // translations on the right; an item crosses to the other side when its own would push it SWITCH below its line
  // and the other side is free sooner. Each side keeps its own floor.
  const two = twoSide.matches;
  body.classList.toggle("two-side", two);
  const SWITCH = 3 * rem;
  for (const [, n] of pairs) n.classList.remove("mn-l");
  // margin widths are read after the class change, so heights are measured in the column each item will use
  const anchors = pairs.map(([m]) => tops.get(m));
  const heights = pairs.map(([, n]) => n.getBoundingClientRect().height);
  let buttonH = null;
  const floors = { r: -Infinity, l: -Infinity };
  let floor = -Infinity;
  let stack = null; // {block, notes, button}
  pairs.forEach(([marker, note], i) => {
    const block = blockOf(marker);
    const anchor = anchors[i];
    let side = "r";
    if (two) {
      const pref = note.classList.contains("mn-gw") ? "l" : "r", other = pref === "l" ? "r" : "l";
      const yp = Math.max(anchor, floors[pref] + GAP), yo = Math.max(anchor, floors[other] + GAP);
      side = yp - anchor > SWITCH && yo < yp ? other : pref;
    }
    floor = floors[side];
    const y = Math.max(anchor, floor + GAP);
    const overflow = y - anchor > LIMIT && !expanded.has(block);
    if (overflow || (stack && stack.block === block)) {
      note.classList.add("sn-stacked");
      asPopover(note, true);
      if (!stack || stack.block !== block) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = side === "l" ? "sn-more mn-l" : "sn-more";
        button.setAttribute("aria-expanded", "false");
        button.style.top = `${y}px`;
        article.appendChild(button);
        button.addEventListener("click", () => { expanded.add(block); layoutNotes(); });
        stack = { block, notes: [], button };
        if (buttonH === null) { button.textContent = "1 more note"; buttonH = button.getBoundingClientRect().height; }
        floors[side] = y + buttonH;
      }
      stack.notes.push(note);
      const n = stack.notes.length;
      stack.button.textContent = `${n} more note${n > 1 ? "s" : ""}`;
      stack.button.setAttribute("aria-label", `${n} more note${n > 1 ? "s" : ""} for this paragraph: show them in the margin`);
      return;
    }
    stack = null;
    note.classList.toggle("mn-l", side === "l");
    note.style.top = `${y}px`;
    floors[side] = y + heights[i];
  });
  const end = Math.max(floors.r, floors.l);
  article.style.minHeight = end > 0 ? `${Math.ceil(end)}px` : "";
}

let pending = 0;
function scheduleLayout() {
  if (!article) return;
  cancelAnimationFrame(pending);
  pending = requestAnimationFrame(layoutNotes);
}
if (article) {
  wide.addEventListener("change", () => { expanded.clear(); scheduleLayout(); });
  twoSide.addEventListener("change", () => { expanded.clear(); scheduleLayout(); });
  window.addEventListener("resize", scheduleLayout);
  document.fonts?.ready.then(scheduleLayout);
  window.addEventListener("load", scheduleLayout);
  new ResizeObserver(scheduleLayout).observe(article);
}

// ---------------------------------------------------------------- what each note is on
// Each margin item covers some of Burton's words (owner, 2026-11-03, T4 B): a note of his, the words from its
// marker to the next stop; a translation, its passage; one of Gowland's notes, the words it is on. Hovering either
// lights both; a click on those words, or on the item, pins them. The words are lit with the CSS Highlight API, so
// the text's markup is never changed.
const SKIP = ".sidenote, .mn, .ft, .nref, .mref, .gowland-tr, .gowland-verse, .cx-b, .sr-only, .st-mark, .prov";
const STOP = /[,;:.!?)]/;
const spans = new Map(); // margin item -> Range over its words

function textAfter(start, block, accept) {
  // walk the visible text after `start` inside `block`; accept(text node, offset) returns an end offset or -1
  const walker = document.createTreeWalker(block, NodeFilter.SHOW_TEXT,
    { acceptNode: (n) => n.parentElement.closest(SKIP) ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT });
  walker.currentNode = start;
  let first = null, last = null;
  for (let n = walker.nextNode(); n; n = walker.nextNode()) {
    if (!start.compareDocumentPosition || !(start.compareDocumentPosition(n) & Node.DOCUMENT_POSITION_FOLLOWING)) continue;
    first ||= n;
    const end = accept(n);
    if (end >= 0) { last = [n, end]; break; }
    last = [n, n.length];
  }
  if (!first || !last) return null;
  const r = document.createRange();
  r.setStart(first, 0);
  r.setEnd(last[0], last[1]);
  return r;
}

function spanOf(marker) {
  const block = blockOf(marker);
  if (marker.dataset.fo) {
    const fo = document.querySelector(`.fp[data-fid="${CSS.escape(marker.dataset.fo)}"] > .fo`);
    if (!fo) return null;
    const r = document.createRange();
    r.selectNodeContents(fo);
    return r;
  }
  if (marker.classList.contains("mref")) {
    let left = Number(marker.dataset.len || 0);
    if (!left) return null;
    return textAfter(marker, block, (n) => { if (n.length >= left) return left; left -= n.length; return -1; });
  }
  let lead = true; // skip the space after the marker, then stop before the next punctuation
  return textAfter(marker, block, (n) => {
    const s = n.data;
    for (let i = 0; i < s.length; i++) {
      if (lead && /\s/.test(s[i])) continue;
      lead = false;
      if (STOP.test(s[i])) return i;
    }
    return -1;
  });
}

const canHighlight = typeof Highlight === "function" && CSS.highlights;
let hot = null, pinned = null;
function light(item) {
  if (hot === item) return;
  hot?.classList.remove("hot");
  hot = item;
  item?.classList.add("hot");
  if (!canHighlight) return;
  const ranges = [item, pinned].filter(Boolean).map((i) => spans.get(i)).filter(Boolean);
  CSS.highlights.set("note-words", new Highlight(...ranges));
}
function pin(item) {
  pinned?.classList.remove("pinned");
  pinned = pinned === item ? null : item;
  pinned?.classList.add("pinned");
  hot = null;
  light(item);
}

if (article) {
  for (const m of markers) {
    const item = noteOf(m);
    if (!item) continue;
    try { const r = spanOf(m); if (r && !r.collapsed) spans.set(item, r); } catch { /* a block the walker cannot read */ }
    item.addEventListener("mouseenter", () => light(item));
    item.addEventListener("mouseleave", () => light(pinned));
    item.addEventListener("click", (ev) => { if (!ev.target.closest("a, summary, .prov")) pin(item); });
  }
  const at = (ev) => {
    const pos = document.caretPositionFromPoint?.(ev.clientX, ev.clientY);
    const node = pos ? pos.offsetNode : document.caretRangeFromPoint?.(ev.clientX, ev.clientY)?.startContainer;
    const off = pos ? pos.offset : document.caretRangeFromPoint?.(ev.clientX, ev.clientY)?.startOffset;
    if (!node) return null;
    let best = null, size = Infinity;
    for (const [item, r] of spans) {
      try {
        if (!r.isPointInRange(node, off)) continue;
        const s = r.toString().length;
        if (s < size) { best = item; size = s; }
      } catch { /* node in another tree */ }
    }
    return best;
  };
  let frame = 0;
  article.addEventListener("mousemove", (ev) => {
    if (ev.target.closest(".sidenote, .mn, .sn-more")) return;
    cancelAnimationFrame(frame);
    frame = requestAnimationFrame(() => light(at(ev) || pinned));
  });
  article.addEventListener("mouseleave", () => light(pinned));
  // keyboard: focusing a passage lights its card (and the card reads out through aria-describedby on narrow screens)
  article.addEventListener("focusin", (ev) => {
    const fid = ev.target.closest?.(".fp")?.dataset.fid;
    const card = fid && document.getElementById(`mt-${fid}`);
    if (card) light(card);
  });
  article.addEventListener("focusout", () => light(pinned));
  article.addEventListener("click", (ev) => {
    if (ev.target.closest("a, button, .sidenote, .mn, summary") || getSelection().toString()) return;
    const item = at(ev);
    if (!item) return;
    if (wide.matches && !item.classList.contains("sn-stacked")) pin(item);
    else if (canPopover) { // narrow screens: the item opens beside the words tapped
      closeNote(false);
      asPopover(item, true);
      item.showPopover();
      placePopover(item, { getBoundingClientRect: () => new DOMRect(ev.clientX, ev.clientY - 12, 1, 22) });
    }
  });
  document.addEventListener("keydown", (ev) => { if (ev.key === "Escape" && pinned) pin(pinned); });
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
    else if (body.classList.contains("mode-gloss") && (!body.classList.contains("mn-on") || fp.closest(".sidenote"))) {
      fp.classList.toggle("pinned");
    }
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
