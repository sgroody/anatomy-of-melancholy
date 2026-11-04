// Reading options, notes and translation behaviour. Progressive enhancement: the text and
// Burton's notes are readable without this script.

const KEY = "burton-settings";
const root = new URL("..", import.meta.url);
const html = document.documentElement;
const body = document.body;
const wide = window.matchMedia("(min-width: 1100px)");
const twoSide = window.matchMedia("(min-width: 1380px)"); // room for a margin on each side (R3)
// the margins are in use: a wide window, and no facing translation taking their room (stage 4)
const isWide = () => wide.matches && !body.classList.contains("facing-on");
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

// the light/dark switch in the running head (owner, 2026-11-04): flips whatever is showing, and remembers it
const darkNow = () => html.dataset.theme === "dark" ||
  (!html.dataset.theme && window.matchMedia("(prefers-color-scheme: dark)").matches);
document.querySelector(".theme-toggle")?.addEventListener("click", () => {
  settings.theme = darkNow() ? "light" : "dark";
  save(settings);
  syncInputs();
  apply();
});

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
const opened = new WeakSet(); // notes the reader opened to read whole
const FOLD_LINES = 4, FOLD_SHORT = 2, FOLD_ONE = 1; // how many lines a shortened note keeps
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
    checkFolds(note);
    placePopover(note, marker);
  } else {
    note.classList.add("open"); // inline expansion fallback
    checkFolds(note);
  }
}

// Bible verses (KJV, stage 6) are folded after three lines; "more" shows only where the fold hides something.
// Without this script they are shown whole.
function checkFolds(scope) {
  for (const k of scope.querySelectorAll(".kjv.fold:not(.open)")) {
    const t = k.querySelector(".kjv-t");
    k.querySelector(".kjv-more").hidden = !(t && t.scrollHeight > t.clientHeight + 1);
  }
}
for (const k of document.querySelectorAll(".kjv")) {
  k.classList.add("fold");
  const more = k.querySelector(".kjv-more");
  more?.addEventListener("click", (ev) => {
    ev.stopPropagation();
    const open = k.classList.toggle("open");
    more.textContent = open ? "less" : "more";
    more.setAttribute("aria-expanded", String(open));
    scheduleLayout();
  });
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
    if (isWide() && !note.classList.contains("sn-stacked")) {
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
  body.classList.toggle("mn-on", isWide());
  if (!isWide()) {
    article.classList.remove("sn-laid");
    article.style.minHeight = "";
    notes.forEach((n) => { n.classList.remove("sn-stacked", "mn-fold"); n.style.top = ""; asPopover(n, true); });
    return;
  }
  closeNote(false);
  article.classList.add("sn-laid");
  // The browser lays the page out a fixed number of times, not once per note (M8: the longest page took 1.4 s):
  // (1) every note into the margin, unshortened; (2) read every marker's place and every note's height, which do not
  // depend on each other, since laid-out notes are out of the flow; (3) place them, in arithmetic only.
  // With translations in the line (stage 7), their margin cards are not shown and take no room.
  const inLine = body.classList.contains("mode-english");
  const all = markers.map((m) => [m, noteOf(m)]).filter(([, n]) => n && !(inLine && n.classList.contains("mn-tr")));
  for (const [, note] of all) {
    note.classList.remove("sn-stacked", "mn-fold", "mn-fold2", "mn-fold3", "mn-l");
    asPopover(note, false);
    note.style.top = "";
  }
  checkFolds(article);
  const rem = parseFloat(getComputedStyle(article).fontSize);
  const LIMIT = 14 * rem; // a note further than this below its marker makes the notes around it shorten
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
  const anchors = pairs.map(([m]) => tops.get(m));
  const full = pairs.map(([, n]) => n.getBoundingClientRect().height);
  // Nothing is held back (owner, 2026-11-04): where notes would drift too far below their words, the long ones in that
  // stretch are shortened to FOLD_LINES lines, with "more" to read them whole (which pushes the rest down).
  // A second, shorter fold (FOLD_SHORT lines) is used only where the first is not enough (one margin, many notes).
  const noteSize = pairs.length ? parseFloat(getComputedStyle(pairs[0][1]).fontSize) : rem;
  const foldHs = [Infinity, ...[FOLD_LINES, FOLD_SHORT, FOLD_ONE].map((n) => n * 1.35 * noteSize)];
  const place = (h) => {
    const floors = { r: -Infinity, l: -Infinity }, ys = [], sides = [];
    pairs.forEach(([, note], i) => {
      const anchor = anchors[i];
      let side = "r";
      if (two) {
        const pref = note.classList.contains("mn-gw") ? "l" : "r", other = pref === "l" ? "r" : "l";
        const yp = Math.max(anchor, floors[pref] + GAP), yo = Math.max(anchor, floors[other] + GAP);
        side = yp - anchor > SWITCH && yo < yp ? other : pref;
      }
      const y = Math.max(anchor, floors[side] + GAP);
      ys.push(y);
      sides.push(side);
      floors[side] = y + h[i];
    });
    return { ys, sides, floors };
  };
  const h = full.slice(), fold = pairs.map(() => 0); // 0 whole, 1 four lines, 2 two lines, 3 one line
  let p = place(h);
  for (let round = 0; round < 8; round++) {
    let changed = false;
    p.ys.forEach((y, i) => {
      if (y - anchors[i] <= LIMIT) return;
      let j = i; // back to where the run of pushed notes began
      while (j > 0 && p.ys[j] > anchors[j] + 1) j--;
      const level = Math.min(3, 1 + Math.floor(round / 2)); // two rounds of each fold, shortest last
      for (let k = j; k <= i; k++) {
        if (fold[k] < level && !opened.has(pairs[k][1]) && full[k] > foldHs[level] * 1.3) {
          fold[k] = level; h[k] = foldHs[level]; changed = true;
        }
      }
    });
    if (!changed && round >= 4) break;
    if (changed) p = place(h);
  }
  pairs.forEach(([, note], i) => {
    note.classList.toggle("mn-l", p.sides[i] === "l");
    note.classList.toggle("mn-fold", fold[i] > 0);
    note.classList.toggle("mn-fold2", fold[i] === 2);
    note.classList.toggle("mn-fold3", fold[i] === 3);
    if (fold[i] && !note.querySelector(":scope > .fold-more")) {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "fold-more";
      b.textContent = "more";
      b.setAttribute("aria-label", "Show the whole note");
      b.addEventListener("click", (ev) => { ev.stopPropagation(); opened.add(note); scheduleLayout(); });
      note.append(b);
    }
    note.style.top = `${p.ys[i]}px`;
  });
  const end = Math.max(p.floors.r, p.floors.l);
  article.style.minHeight = end > 0 ? `${Math.ceil(end)}px` : "";
}

let pending = 0;
function scheduleLayout() {
  if (!article) return;
  cancelAnimationFrame(pending);
  pending = requestAnimationFrame(layoutNotes);
}
if (article) {
  wide.addEventListener("change", scheduleLayout);
  twoSide.addEventListener("change", scheduleLayout);
  // a "+ more" opened or closed inside a note changes its height: the notes below move with it
  article.addEventListener("toggle", (ev) => { if (ev.target.closest?.(".mn, .sidenote")) scheduleLayout(); }, true);
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
const SKIP = ".sidenote, .mn, .ft, .ftr, .nref, .mref, .gowland-tr, .gowland-verse, .cx-b, .sr-only, .st-mark, .prov";
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
// A word with several notes (a gloss inside a passage with a broader note) lights all of them (owner, 2026-11-04).
let hot = [], pinned = null;
function light(items) {
  items = [items].flat().filter(Boolean);
  if (items.length === hot.length && items.every((x, i) => x === hot[i])) return;
  hot.forEach((x) => x.classList.remove("hot"));
  hot = items;
  hot.forEach((x) => x.classList.add("hot"));
  if (!canHighlight) return;
  const ranges = [...hot, pinned].filter(Boolean).map((i) => spans.get(i)).filter(Boolean);
  CSS.highlights.set("note-words", new Highlight(...ranges));
}
function pin(item) {
  pinned?.classList.remove("pinned");
  pinned = pinned === item ? null : item;
  pinned?.classList.add("pinned");
  hot = [];
  light(item);
}

if (article) {
  for (const m of markers) {
    const item = noteOf(m);
    if (!item) continue;
    try { const r = spanOf(m); if (r && !r.collapsed) spans.set(item, r); } catch { /* a block the walker cannot read */ }
    item.addEventListener("mouseenter", () => light(item));
    item.addEventListener("mouseleave", () => light(pinned));
    item.addEventListener("click", (ev) => { if (!ev.target.closest("a, summary, .prov, button")) pin(item); });
  }
  const at = (ev) => {
    const pos = document.caretPositionFromPoint?.(ev.clientX, ev.clientY);
    const node = pos ? pos.offsetNode : document.caretRangeFromPoint?.(ev.clientX, ev.clientY)?.startContainer;
    const off = pos ? pos.offset : document.caretRangeFromPoint?.(ev.clientX, ev.clientY)?.startOffset;
    if (!node) return [];
    const found = [];
    for (const [item, r] of spans) {
      try { if (r.isPointInRange(node, off)) found.push([r.toString().length, item]); } catch { /* another tree */ }
    }
    return found.sort((a, b) => a[0] - b[0]).map(([, item]) => item); // the narrowest first
  };
  let frame = 0;
  article.addEventListener("mousemove", (ev) => {
    if (ev.target.closest(".sidenote, .mn, .sn-more")) return;
    cancelAnimationFrame(frame);
    frame = requestAnimationFrame(() => { const items = at(ev); light(items.length ? items : pinned); });
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
    const item = at(ev)[0];
    if (!item) return;
    if (isWide() && !item.classList.contains("sn-stacked")) pin(item);
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

// A long passage set facing its translation (stage 7, T12 B): pointing at a line lights it and its translation.
for (const fp of document.querySelectorAll(".fp-facing")) {
  const lines = [...fp.querySelectorAll("[data-r]")];
  const lit = (r) => lines.forEach((x) => x.classList.toggle("hot", r != null && x.dataset.r === r));
  fp.addEventListener("mouseover", (ev) => lit(ev.target.closest("[data-r]")?.dataset.r));
  fp.addEventListener("mouseleave", () => lit(null));
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

// ---------------------------------------------------------------- windows on names and cross-references (stage 5)
// Hovering a cited author's name or a cross-reference opens a window: the author's entry, or the opening of the
// passage referred to. Held still on the link, a bar fills along the window's foot; once full, the window stays
// while the pointer moves into it (CK3-style), and names inside it open windows of their own. A click follows the
// link. Esc closes them all.
const authorsData = Object.assign({}, ...[...document.querySelectorAll("script.authors-data")].map((s) => {
  try { return JSON.parse(s.textContent); } catch { return {}; }
}));
const previews = new Map(); // href -> Promise of {title, text}
function el(tag, cls, text) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text != null) e.textContent = text;
  return e;
}
function preview(href) {
  if (!previews.has(href)) {
    previews.set(href, fetch(href).then((r) => r.text()).then((t) => {
      const d = new DOMParser().parseFromString(t, "text/html");
      const art = d.querySelector("article.unit");
      art?.querySelectorAll(".sidenote, .nref, .mn-pool, .mref, .ft, .ftr, .gowland-tr, .cx-b, .ic-m, .sr-only, .ini, script")
        .forEach((x) => x.remove());
      const p = art && [...art.querySelectorAll("p")].find((x) => !x.matches("[class*=head]") && x.textContent.trim());
      const text = (p?.textContent || "").replace(/­/g, "").replace(/\s+/g, " ").trim();
      return { title: d.querySelector("h1")?.textContent.trim() || "", text: text.length > 420 ? text.slice(0, 420) + "…" : text };
    }).catch(() => null));
  }
  return previews.get(href);
}
async function windowFor(trig) {
  const box = document.createDocumentFragment();
  if (trig.classList.contains("nm")) {
    const a = authorsData[trig.dataset.author];
    if (!a) return null;
    box.append(el("p", "pw-h", a.name + (a.dates ? `, ${a.dates}` : "")));
    if (a.about) {
      const p = el("p", "pw-t", a.about + " ");
      if (a.by) {
        const pv = el("span", "prov");
        const full = `Entry drafted by ${a.by}${a.checked ? ", checked by the owner" : ", not yet checked"}`;
        pv.title = full;
        pv.setAttribute("aria-label", full);
        pv.setAttribute("role", "img");
        p.append(pv);
      }
      box.append(p);
    }
    const links = el("p", "pw-l");
    const entry = el("a", null, "Index entry");
    entry.href = trig.href;
    links.append(entry);
    if (a.qid) {
      const w = el("a", null, "Wikipedia");
      w.href = `https://www.wikidata.org/wiki/Special:GoToLinkedPage/enwiki/${encodeURIComponent(a.qid)}`;
      w.rel = "noopener";
      w.target = "_blank";
      links.append(" · ", w);
    }
    box.append(links);
    return box;
  }
  const pv = await preview(trig.href);
  if (!pv) return null;
  box.append(el("p", "pw-h", pv.title), el("p", "pw-t", pv.text));
  const open = el("a", "pw-open", "Open this passage →");
  open.href = trig.href;
  box.append(el("p", "pw-l"));
  box.lastChild.append(open);
  return box;
}
const pops = []; // the open windows, outermost first: {el, trig, locked, lt, ct}
function closeFrom(i) {
  while (pops.length > i) { const p = pops.pop(); clearTimeout(p.lt); clearTimeout(p.ct); p.el.remove(); }
}
function levelOf(node) {
  const w = node.closest?.(".pw");
  return w ? pops.findIndex((p) => p.el === w) + 1 : 0;
}
async function openWindow(trig) {
  const lvl = levelOf(trig);
  if (pops[lvl]?.trig === trig) { clearTimeout(pops[lvl].ct); return; }
  closeFrom(lvl);
  const p = { trig, locked: false };
  pops.push(p);
  const content = await windowFor(trig);
  if (!content || pops[lvl] !== p) { if (pops[lvl] === p) closeFrom(lvl); return; }
  const w = el("div", "pw");
  w.setAttribute("role", "dialog");
  w.append(content, el("span", "pw-bar"));
  document.body.append(w);
  p.el = w;
  const r = trig.getBoundingClientRect();
  const left = Math.max(16, Math.min(r.left, innerWidth - w.offsetWidth - 16));
  const below = r.bottom + 8 + w.offsetHeight < innerHeight || r.top < w.offsetHeight + 16;
  w.style.left = `${left + scrollX}px`;
  w.style.top = `${(below ? r.bottom + 6 : r.top - w.offsetHeight - 6) + scrollY}px`;
  p.lt = setTimeout(() => { p.locked = true; w.classList.add("locked"); }, 650);
  w.addEventListener("mouseenter", () => { clearTimeout(p.ct); pops.slice(0, lvl).forEach((q) => clearTimeout(q.ct)); });
  w.addEventListener("mouseleave", (ev) => {
    if (ev.relatedTarget && pops.slice(lvl + 1).some((q) => q.el?.contains(ev.relatedTarget))) return;
    p.ct = setTimeout(() => closeFrom(lvl), 300);
  });
}
const POP = "a.nm, a.xref";
let hoverTimer = 0;
document.addEventListener("mouseover", (ev) => {
  const t = ev.target.closest?.(POP);
  if (!t || !wide.matches) return;
  clearTimeout(hoverTimer);
  hoverTimer = setTimeout(() => openWindow(t), 120);
});
document.addEventListener("mouseout", (ev) => {
  const t = ev.target.closest?.(POP);
  if (!t) return;
  clearTimeout(hoverTimer);
  const lvl = levelOf(t), p = pops[lvl];
  if (!p || p.trig !== t) return;
  if (!p.locked) { closeFrom(lvl); return; }
  if (ev.relatedTarget && p.el?.contains(ev.relatedTarget)) return;
  p.ct = setTimeout(() => closeFrom(lvl), 350);
});
document.addEventListener("keydown", (ev) => { if (ev.key === "Escape") closeFrom(0); });

// ---------------------------------------------------------------- the front page (stage 4)
// Pointing at a panel of the engraving shows its stanza beside it (owner, 2026-11-03: T14, R4 B).
const stanzaBox = document.querySelector(".front-stanza");
if (stanzaBox) {
  const show = (st) => stanzaBox.querySelectorAll(".fs-st").forEach((d) => { d.hidden = d.dataset.st !== st; });
  for (const a of document.querySelectorAll(".front .fs-panel")) {
    a.addEventListener("mouseenter", () => show(a.dataset.st));
    a.addEventListener("focus", () => show(a.dataset.st));
  }
}

// ---------------------------------------------------------------- facing translations (stage 4)
// A Latin poem of the front matter with Gowland's translation beside it (private build): his page is fetched and
// set in a second column; Burton's notes then open as pop-ups, the margins being taken.
for (const a of document.querySelectorAll("a[data-facing]")) {
  let col = null;
  const open = async () => {
    if (!col) {
      try {
        const page = new DOMParser().parseFromString(await (await fetch(a.href)).text(), "text/html");
        const art = page.querySelector("article.unit");
        if (!art || !article) return;
        col = document.createElement("aside");
        col.className = "facing-t";
        col.dataset.resp = "gowland";
        col.setAttribute("aria-label", a.textContent);
        art.querySelectorAll("[id]").forEach((e) => e.removeAttribute("id"));
        col.append(...art.childNodes);
        article.after(col);
      } catch { return; }
    }
    col.hidden = false;
    body.classList.add("facing-on");
    a.setAttribute("aria-expanded", "true");
    scheduleLayout();
  };
  const close = () => {
    if (col) col.hidden = true;
    body.classList.remove("facing-on");
    a.setAttribute("aria-expanded", "false");
    scheduleLayout();
  };
  a.setAttribute("aria-expanded", "false");
  a.addEventListener("click", (ev) => {
    ev.preventDefault();
    if (body.classList.contains("facing-on")) close(); else open();
  });
  if (wide.matches) open();
}

apply();

// ---------------------------------------------------------------- offline (installable app)
if ("serviceWorker" in navigator && location.protocol.startsWith("http")) {
  navigator.serviceWorker.register(new URL("sw.js", root)).catch(() => {});
}
