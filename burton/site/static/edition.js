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
const DEFAULTS = { mode: "gloss", theme: "auto", size: "m", gowland: false, pages: false, order: "default", cites: false, glosses: false,
  latin: "oxblood", laLight: "#7a2230", laDark: "#e0c27a", // the colour of the Latin (round 5, F2)
  textonly: false, // the text as printed, with Burton's own notes only (owner, 2026-11-18; his notes kept 2026-11-20)
  // the margin's notes, each source on or off (owner, 2026-11-20); nCites off puts Burton's own citations back in the line;
  // the notes restored from Democritus Minor's edition start off (owner, 2026-11-20)
  nBurton: true, nRestored: false, nGowland: true, nTrans: true, nCites: true, nKjv: true, v: 2 };
const NOTE_SOURCES = { nBurton: "burton", nRestored: "restored", nGowland: "gowland", nTrans: "trans", nCites: "cites",
  nKjv: "kjv" };
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

// which source a margin note is from, for the switches above (the class names are the build's)
const noteSource = (n) => n.classList.contains("sn-restored") ? "restored" : n.classList.contains("sidenote") ? "burton"
  : n.classList.contains("mn-gw") ? "gowland" : n.matches(".mn-tr, .mn-own") ? "trans" : n.classList.contains("mn-ic") ? "cites"
  : "other";
const settings = Object.assign({}, DEFAULTS, load());
// settings saved before 2026-11-20: "Hide in-line citations" now means Burton's own citations in the line, and "Only
// Gowland's notes" is the margin with every other source switched off
if (settings.hideic) settings.nCites = false;
if (settings.onlygw) Object.assign(settings, { nBurton: false, nRestored: false, nTrans: false, nCites: false, nKjv: false });
delete settings.hideic; delete settings.onlygw;
// settings saved before v2 stored the old default for the restored notes (on); the new default stands once
if ((settings.v || 1) < 2) { settings.nRestored = false; settings.v = 2; }

// the page's number in the top left corner: A beside the contents in the running head (the default), B in the window's
// corner as Burton's own heads print it, following the reader down; ?uid=B to compare, ?uid=A back (owner, 2026-11-20)
(() => {
  let v = new URLSearchParams(location.search).get("uid");
  try {
    if (v) localStorage.setItem("burton-uid", v.toUpperCase());
    else v = localStorage.getItem("burton-uid");
  } catch { /* private window: this page only */ }
  v = (v || "A").toUpperCase();
  if (v === "A") delete html.dataset.uid;
  else html.dataset.uid = v;
})();

// round 8, F1: the front matter's contents as A (the default), or B or D to compare on the real pages; ?fm=B or ?fm=D
// is remembered from page to page, ?fm=A goes back (owner, 2026-11-19: "I want to see how A, B and D look")
(() => {
  let fm = new URLSearchParams(location.search).get("fm");
  try {
    if (fm) localStorage.setItem("burton-fm", fm.toUpperCase());
    else fm = localStorage.getItem("burton-fm");
  } catch { /* private window: this page only */ }
  fm = (fm || "A").toUpperCase();
  if (fm === "A") delete html.dataset.fm;
  else html.dataset.fm = fm;
})();

function apply() {
  body.classList.remove("mode-gloss", "mode-interlinear", "mode-english");
  // nothing but the text: the original as printed, whatever the other options say (owner, 2026-11-19)
  const bare = !!settings.textonly;
  body.classList.add(`mode-${bare ? "gloss" : settings.mode}`);
  if (settings.theme === "auto") delete html.dataset.theme;
  else html.dataset.theme = settings.theme;
  if (settings.size === "m") delete html.dataset.size;
  else html.dataset.size = settings.size;
  if (settings.latin === "oxblood") delete html.dataset.latin;
  else html.dataset.latin = settings.latin;
  html.style.setProperty("--la-c-light", settings.laLight);
  html.style.setProperty("--la-c-dark", settings.laDark);
  body.classList.toggle("show-gowland", !bare && !!settings.gowland);
  body.classList.toggle("show-pages", !bare && !!settings.pages);
  body.classList.toggle("show-abbr", bare || !!settings.cites); // "Burton's abbreviations" in place of the expansions
  body.classList.toggle("show-glosses", !bare && !!settings.glosses);
  for (const [k, cls] of Object.entries(NOTE_SOURCES)) body.classList.toggle(`no-${cls}`, !bare && !settings[k]);
  body.classList.toggle("text-only", !!settings.textonly);
  document.querySelectorAll(".print-toggle").forEach((b) => b.setAttribute("aria-pressed", String(bare)));
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
    else if (input.type === "color") input.value = settings[input.name];
    else input.checked = !!settings[input.name];
  }
}
for (const input of document.querySelectorAll(".settings input")) {
  input.addEventListener("change", () => {
    settings[input.name] = input.type === "radio" || input.type === "color" ? input.value : input.checked;
    if (input.type === "color") { settings.latin = "custom"; syncInputs(); } // a colour chosen: one's own colours
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
// beside it, the text as printed: Burton's words and his own notes, nothing the edition adds (owner, 2026-11-20)
document.querySelector(".print-toggle")?.addEventListener("click", () => {
  settings.textonly = !settings.textonly;
  save(settings);
  syncInputs();
  apply();
});

// the search box opens in the running head; Enter goes to the results (owner, 2026-11-18)
const hsearch = document.querySelector(".hsearch");
document.querySelector(".search-link:not([aria-current])")?.addEventListener("click", (ev) => {
  if (!hsearch) return;
  ev.preventDefault();
  const open = hsearch.classList.toggle("open");
  if (open) hsearch.querySelector("input").focus();
});
hsearch?.addEventListener("keydown", (ev) => {
  if (ev.key === "Escape") { hsearch.classList.remove("open"); document.querySelector(".search-link")?.focus(); }
});

const panel = document.getElementById("settings");
const toggle = document.querySelector(".settings-toggle");
function setPanel(open, focusToggle) {
  panel.hidden = !open;
  toggle.setAttribute("aria-expanded", String(open));
  // the chosen way of reading the foreign passages first (the first checked radio), not a switch above it
  if (open) (panel.querySelector('input[type="radio"]:checked') || panel.querySelector("input"))?.focus();
  else if (focusToggle) toggle.focus();
}
if (panel && toggle) {
  toggle.addEventListener("click", () => setPanel(panel.hidden, false));
  // a way out (owner, 2026-11-20): the × at the panel's corner, Escape, or a click anywhere outside it
  panel.querySelector(".settings-close")?.addEventListener("click", () => setPanel(false, true));
  document.addEventListener("click", (ev) => {
    if (!panel.hidden && !panel.contains(ev.target) && !toggle.contains(ev.target)) setPanel(false, false);
  });
  panel.addEventListener("keydown", (ev) => {
    if (ev.key === "Escape") { ev.stopPropagation(); setPanel(false, true); }
  });
  // the wheel over the open options scrolls the options, never the page behind them (owner, 2026-11-20); the CSS's
  // overscroll-behavior stops the page at the panel's ends, this stops it where the panel has nothing to scroll
  panel.addEventListener("wheel", (ev) => {
    if (panel.scrollHeight <= panel.clientHeight + 1) ev.preventDefault();
  }, { passive: false });
}

// The search, options and light/dark signs follow the reader down the page once the running head has scrolled away
// (owner, 2026-11-19: "a small floating settings widget [that follows] you down the page in the upper right")
const siteHead = document.querySelector("header.site");
if (siteHead && "IntersectionObserver" in window) {
  new IntersectionObserver(([e]) => body.classList.toggle("bar-float", !e.isIntersecting && e.boundingClientRect.top < 0))
    .observe(siteHead);
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
  // and what the reader chose not to see takes no room either (owner, 2026-11-18)
  // as printed, Burton's own notes and nothing else (owner, 2026-11-20)
  const shown = (n) => body.classList.contains("text-only") ? noteSource(n) === "burton" :
    !body.classList.contains(`no-${noteSource(n)}`) &&
    !(n.classList.contains("mn-gl") && !body.classList.contains("show-glosses"));
  const all = markers.map((m) => [m, noteOf(m)])
    .filter(([, n]) => n && shown(n) && !(inLine && n.classList.contains("mn-tr")));
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
  // a page set facing Gowland keeps one margin: his notes stand between the columns (stage 9)
  // and so does a front-matter page whose contents stand in the left margin (round 8, F1 D)
  const two = twoSide.matches && !article.querySelector(".fp-wide, .ded-wrap") &&
    !(html.dataset.fm === "D" && document.querySelector(".front-nav"));
  body.classList.toggle("two-side", two);
  const SWITCH = 3 * rem;
  const anchors = pairs.map(([m]) => tops.get(m));
  const full = pairs.map(([, n]) => n.getBoundingClientRect().height);
  // Nothing is held back (owner, 2026-11-04): where notes would drift too far below their words, the long ones in that
  // stretch are shortened to FOLD_LINES lines, with "more" to read them whole (which pushes the rest down).
  // A second, shorter fold (FOLD_SHORT lines) is used only where the first is not enough (one margin, many notes).
  const noteSize = pairs.length ? parseFloat(getComputedStyle(pairs[0][1]).fontSize) : rem;
  const foldHs = [Infinity, ...[FOLD_LINES, FOLD_SHORT, FOLD_ONE].map((n) => n * 1.35 * noteSize)];
  const place = (h, fold) => {
    const floors = { r: -Infinity, l: -Infinity }, ys = [], sides = [];
    pairs.forEach(([, note], i) => {
      const anchor = anchors[i];
      let side = "r";
      if (two) {
        const pref = note.classList.contains("mn-gw") ? "l" : "r", other = pref === "l" ? "r" : "l";
        const yp = Math.max(anchor, floors[pref] + GAP), yo = Math.max(anchor, floors[other] + GAP);
        side = yp - anchor > SWITCH && yo < yp ? other : pref;
      }
      const y = Math.max(anchor, floors[side] + (fold[i] >= 2 ? GAP / 2 : GAP)); // short notes sit closer
      ys.push(y);
      sides.push(side);
      floors[side] = y + h[i];
    });
    return { ys, sides, floors };
  };
  const h = full.slice(), fold = pairs.map(() => 0); // 0 whole, 1 four lines, 2 two lines, 3 one line
  let p = place(h, fold);
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
    if (changed) p = place(h, fold);
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
  if (marker.dataset.note) { // Gowland on words of Burton's sidenote (stage 11): those words, inside the note
    const note = document.getElementById(marker.dataset.note), words = marker.dataset.words;
    const walker = note && document.createTreeWalker(note, NodeFilter.SHOW_TEXT);
    for (let n = walker?.nextNode(); n; n = walker.nextNode()) {
      const i = n.data.indexOf(words);
      if (i >= 0) { const r = document.createRange(); r.setStart(n, i); r.setEnd(n, i + words.length); return r; }
    }
    return null;
  }
  if (marker.dataset.back === "clause") { // an in-line Bible reference: the clause before it, back to a stop
    const walker = document.createTreeWalker(block, NodeFilter.SHOW_TEXT,
      { acceptNode: (n) => n.parentElement.closest(SKIP) ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT });
    const nodes = [];
    for (let n = walker.nextNode(); n; n = walker.nextNode()) {
      if (marker.compareDocumentPosition(n) & Node.DOCUMENT_POSITION_PRECEDING) nodes.push(n);
    }
    let end = null, start = null;
    for (let k = nodes.length - 1; k >= 0 && !start; k--) {
      const s = nodes[k].data;
      for (let i = s.length - 1; i >= 0; i--) {
        if (!end) { if (/[\s,;:]/.test(s[i])) continue; end = [nodes[k], i + 1]; }
        if (/[.;:!?]/.test(s[i])) { start = [nodes[k], i + 1]; break; }
      }
      if (!start && k === 0) start = [nodes[0], 0];
    }
    if (!end || !start) return null;
    const r = document.createRange();
    r.setStart(...start);
    r.setEnd(...end);
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
    item.addEventListener("click", (ev) => {
      if (ev.target.closest("a, summary, .prov, button")) return;
      // a shortened note opens whole where it is clicked, not only at its "more" (owner, 2026-11-21); not a translation
      // with its own ▾ for the other versions
      if (item.classList.contains("mn-fold") && !item.querySelector(".mn-more")) { opened.add(item); scheduleLayout(); }
      pin(item);
    });
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
  // a note of Burton's quoting the Latin he also renders in the text: pointing at the note lights his English, and
  // pointing at his English lights the note (owner, 2026-11-18)
  const holder = fp.closest(".sidenote");
  if (holder && mine.length) {
    holder.addEventListener("mouseenter", () => link(true));
    holder.addEventListener("mouseleave", () => link(false));
    mine.forEach((s) => {
      s.addEventListener("mouseenter", () => holder.classList.add("hot"));
      s.addEventListener("mouseleave", () => holder.classList.remove("hot"));
    });
  }
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

// A long note between facing columns (stage 9) is shortened; "more" opens it, "less" shuts it.
document.addEventListener("click", (ev) => {
  const b = ev.target.closest?.(".ftr-more");
  if (!b) return;
  const open = b.closest(".ftr-note").classList.toggle("open");
  b.textContent = open ? "less" : "more";
});

// A long passage set facing its translation (stage 7, T12 B): pointing at a line lights it and its translation.
for (const fp of document.querySelectorAll(".fp-facing")) {
  const lines = [...fp.querySelectorAll("[data-r]")];
  const lit = (r) => lines.forEach((x) => x.classList.toggle("hot", r != null && x.dataset.r === r));
  fp.addEventListener("mouseover", (ev) => lit(ev.target.closest("[data-r]")?.dataset.r));
  fp.addEventListener("mouseleave", () => lit(null));
}

// ---------------------------------------------------------------- the synopses as Burton's sheets (2026-11-19)
// Without script every brace is open. Here: fit each sheet to its width branch by branch (R7), turn tall heads as the
// printer did, fold the braces the page marks to start folded, and open or fold a brace on rest or on a click. The
// rest works like a name's window: the brace fills with rubric, then opens one brace deep; rested on, it fills again
// and the branch is fixed in place; rested on still, its inner braces open one at a time. A branch opened by resting
// but not fixed folds a moment after the pointer leaves it. A Partition on the front page opens onto its sheets only.
const synSheets = [...document.querySelectorAll(".syn-sheet")];
if (synSheets.length) {
  const reduce = matchMedia("(prefers-reduced-motion: reduce)");
  const T_OPEN = 650, T_LAYER = 900, T_PAUSE = 250;  // ms; 650 is the windows' fill; each further layer 900
  const kidsOf = (li) => li.querySelector(":scope > .syn-nb > .syn-kw > .syn-kids");
  const setShut = (li, shut) => {
    li.classList.toggle("syn-shut", shut);
    li.querySelector(":scope > .syn-nb > .syn-kw > .syn-brace")?.setAttribute("aria-expanded", String(!shut));
  };

  // the visible height of every branch (a folded one counts as one level), for the rules without script
  const relevel = (sheet) => {
    const h = new Map();
    for (const li of [...sheet.querySelectorAll(".syn-n")].reverse()) {  // children before parents
      const kids = kidsOf(li);
      if (!kids) { h.set(li, 0); continue; }
      if (li.classList.contains("syn-shut")) { h.set(li, 1); continue; }
      let m = 0;
      for (const c of kids.children) m = Math.max(m, h.get(c) ?? 0);
      h.set(li, 1 + m);
    }
    for (const [li, v] of h) li.dataset.h = v;
  };
  // R7, measured: a branch keeps its head beside its members while its width holds its head (at most 7em, as heads
  // wrap narrow), its brace and what its members need at least; a leaf needs 11em. A head that can be turned takes
  // one line's width. So the deepest branches give way first, as on the printed sheets.
  const ctx = document.createElement("canvas").getContext("2d");
  const fit = (sheet) => {
    sheet.classList.add("syn-fitted");
    const cs = getComputedStyle(sheet), fs = parseFloat(cs.fontSize);
    ctx.font = `${fs}px ${cs.fontFamily}`;
    const lis = [...sheet.querySelectorAll(".syn-n")];
    const need = new Map(), best = new Map(), upright = new Map();
    for (const li of [...lis].reverse()) {
      const kids = kidsOf(li);
      if (!kids) { need.set(li, 11 * fs); best.set(li, 11 * fs); continue; }
      const one = ctx.measureText(li.querySelector(":scope > .syn-nb > .syn-hd").textContent.trim()).width;
      let hw = li.classList.contains("syn-part") ? 14.6 * fs : Math.min(one, 7 * fs) + 0.3 * fs;
      if (li.classList.contains("syn-shut")) { need.set(li, hw + 7.4 * fs); best.set(li, need.get(li)); continue; }
      let m = 0;
      for (const c of kids.children) m = Math.max(m, best.get(c) ?? 0);
      upright.set(li, hw + 0.82 * fs + m);
      const lines = kids.children.length + kids.querySelectorAll(".syn-leaf").length;
      if (!li.matches(".syn-root, .syn-part") && one + 0.6 * fs < lines * 1.26 * fs * 0.6) hw = 1.6 * fs;
      need.set(li, hw + 0.82 * fs + m);
      best.set(li, Math.min(need.get(li), Math.max(11 * fs, m + 0.9 * fs)));
    }
    for (const li of lis) { delete li.dataset.fit; delete li.dataset.turn; }
    for (const li of lis) {  // parents first, so each width read already reflects the parents' choice
      if (!kidsOf(li) || li.offsetParent === null) continue;
      const w = li.getBoundingClientRect().width;
      li.dataset.fit = w < need.get(li) ? "stack" : "side";
      // a head is turned only where the branch has no room for it upright, as the printer turned only to save width
      if (w >= need.get(li) && w < upright.get(li)) li.dataset.turn = "1";
    }
  };
  // R7b: a head that wraps to three lines or more, beside a brace taller than its one-line length, is turned
  const meter = Object.assign(document.createElement("span"), { style: "position:absolute;visibility:hidden;white-space:nowrap;left:-9999px" });
  document.body.append(meter);
  const turn = (sheet) => {
    const hds = [...sheet.querySelectorAll(".syn-n:not(.syn-leaf):not(.syn-shut):not(.syn-root):not(.syn-part) > .syn-nb > .syn-hd")];
    hds.forEach((hd) => hd.classList.remove("syn-rot"));
    const pick = [];
    for (const hd of hds) {
      const nb = hd.parentElement;
      if (nb.closest(".syn-shut") || !nb.parentElement.dataset.turn || getComputedStyle(nb).flexDirection !== "row") continue;
      const cs = getComputedStyle(hd), lh = parseFloat(cs.lineHeight) || 20;
      if (hd.getBoundingClientRect().height < lh * 2.5) continue;
      // the `font` shorthand reads empty under the edition's numeral settings, so its parts are copied
      for (const k of ["fontFamily", "fontSize", "fontStyle", "fontWeight", "letterSpacing"]) meter.style[k] = cs[k];
      meter.innerHTML = hd.innerHTML;
      if (meter.getBoundingClientRect().width + lh * 0.5 < nb.querySelector(":scope > .syn-kw").getBoundingClientRect().height) pick.push(hd);
    }
    pick.forEach((hd) => hd.classList.add("syn-rot"));
  };
  const refresh = (sheet) => { relevel(sheet); fit(sheet); turn(sheet); };
  // after a branch opens or folds: the columns at once, the turned heads once the heights have settled
  const settle = (sheet) => {
    relevel(sheet); fit(sheet);
    clearTimeout(sheet._st);
    sheet._st = setTimeout(() => turn(sheet), reduce.matches ? 0 : 1700);
  };

  // ---- opening and folding
  // Resting fills the brace (and underlines its head) with rubric, as a name's window fills its bar; each time the
  // fill completes, the branch opens one more full layer: first the branch itself, then every brace at its next
  // depth together, and so on while the pointer stays (owner, 2026-11-20: "multiple underlines are good! Each time
  // they finish they should open up another full bracket layer"). What resting opens stays open; a click folds it.
  // The heads of the Partitions and of each sheet's first layer are places to rest too, as they do not move when
  // their branch opens (the brace does).
  let rest = null;  // the trigger rested on: {li, timers, x, y}
  const fill = (li, ms) => {
    li.style.setProperty("--syn-fill", `${reduce.matches ? 0 : ms}ms`);
    li.classList.remove("syn-filling"); void li.offsetWidth; li.classList.add("syn-filling");
  };
  const unfill = (li) => li.classList.remove("syn-filling");
  const later = (fn, ms) => { const t = setTimeout(fn, reduce.matches ? 0 : ms); rest?.timers.push(t); return t; };
  const fix = (li) => li.classList.add("syn-fixed");
  // open one brace deep: the branch's own inner braces folded
  const open = (li) => {
    for (const n of li.querySelectorAll(".syn-n")) if (kidsOf(n)) setShut(n, true);
    setShut(li, false);
    fix(li);
    settle(li.closest(".syn-sheet"));
  };
  const fold = (li) => {
    for (const p of [li, ...li.querySelectorAll(".syn-n")]) p.classList.remove("syn-fixed", "syn-filling");
    setShut(li, true);
    settle(li.closest(".syn-sheet"));
  };
  // the next full layer inside an open branch: every folded brace at the shallowest depth whose way to it is open
  const nextLayer = (li) => {
    const depth = (n) => { let d = 0; for (let p = n.parentElement.closest(".syn-n"); p && p !== li; p = p.parentElement.closest(".syn-n")) d++; return d; };
    const c = [...li.querySelectorAll(".syn-n.syn-shut")].filter((n) => { const a = n.parentElement.closest(".syn-n.syn-shut"); return !a || !li.contains(a); });
    if (!c.length) return [];
    const d = Math.min(...c.map(depth));
    return c.filter((n) => depth(n) === d);
  };
  // open everything in a branch at once (the ⁜ sign of a Partition), or fold it back to its first layer
  const openAll = (li) => {
    for (const n of [li, ...li.querySelectorAll(".syn-n")]) if (kidsOf(n)) { setShut(n, false); fix(n); }
    settle(li.closest(".syn-sheet"));
  };
  const allOpen = (li) => !li.querySelector(".syn-n.syn-shut") && !li.classList.contains("syn-shut");
  const stopRest = () => {
    if (!rest) return;
    rest.timers.forEach(clearTimeout);
    for (const n of [rest.li, ...rest.li.querySelectorAll(".syn-filling")]) unfill(n);
    rest = null;
  };
  // on the front page every brace after the first (a Partition's sheets, once its name has opened, and the layers
  // inside) takes three times as long as the first, so a passing pointer opens the Partition without spilling its
  // sheets (owner, 2026-11-20: twice; 2026-11-21: three times, and for every later brace)
  const stepMs = (li, k) => k === 0 ? T_OPEN : li.closest(".syn-front") ? 3 * T_OPEN : T_LAYER;
  const step = (li, k) => {
    const shut = li.classList.contains("syn-shut");
    if (!shut && !nextLayer(li).length) return;  // nothing more to open
    const ms = stepMs(li, k);
    fill(li, ms);
    later(() => {
      unfill(li);
      if (li.classList.contains("syn-shut")) open(li);
      else { for (const n of nextLayer(li)) { setShut(n, false); fix(n); } settle(li.closest(".syn-sheet")); }
      later(() => step(li, k + 1), T_PAUSE);
    }, ms);
  };
  const startRest = (li, x, y) => {
    stopRest();
    rest = { li, timers: [], x, y };
    step(li, 0);
  };
  const HEADS = ".syn-sheet .syn-part > .syn-nb > .syn-hd, .syn-sheet .syn-root:not(.syn-leaf) > .syn-nb > .syn-hd";
  const triggerOf = (el) => {
    if (el?.closest?.("a, .syn-all, .syn-note")) return null;  // a link or a sign in a head keeps its own work
    return el?.closest?.(`.syn-sheet .syn-brace, ${HEADS}`) || null;
  };

  // Only the reader's own movement counts: an opening branch moves the page under a still pointer (a head narrows to
  // Burton's measure and its brace slides away), and the browser then reports leaving and entering things the pointer
  // never moved over; those are ignored, so a rest lasts until the pointer itself moves off the brace.
  let lastX = -1, lastY = -1, movedAt = 0;
  const moving = () => performance.now() - movedAt < 160;
  document.addEventListener("pointermove", (ev) => {
    if (ev.pointerType === "touch") return;
    if (Math.hypot(ev.clientX - lastX, ev.clientY - lastY) > 1.5) movedAt = performance.now();
    lastX = ev.clientX; lastY = ev.clientY;
    if (!rest || Math.hypot(ev.clientX - rest.x, ev.clientY - rest.y) < 6) return;
    const tr = triggerOf(ev.target);
    if (tr && tr.closest(".syn-n") === rest.li) { rest.x = ev.clientX; rest.y = ev.clientY; } else stopRest();
  });
  document.addEventListener("pointerover", (ev) => {
    if (ev.pointerType === "touch" || (rest && !moving())) return;
    const tr = triggerOf(ev.target);
    if (!tr) return;
    const li = tr.closest(".syn-n");
    if (rest?.li !== li) startRest(li, ev.clientX, ev.clientY);
  });
  document.addEventListener("pointerout", (ev) => {
    if (ev.pointerType === "touch") return;
    if (!ev.relatedTarget) stopRest();  // out of the window
  });
  // keep the clicked brace where it was on screen while the sheet changes around it
  const anchored = (el, fn) => { const y = el.getBoundingClientRect().top; fn(); window.scrollBy(0, el.getBoundingClientRect().top - y); };
  document.addEventListener("click", (ev) => {
    const all = ev.target.closest(".syn-sheet .syn-all");
    if (all) {
      const li = all.closest(".syn-n");
      stopRest();
      if (allOpen(li)) anchored(all, () => { fold(li); });
      else openAll(li);
      all.setAttribute("aria-pressed", String(allOpen(li)));
      return;
    }
    const tr = triggerOf(ev.target);
    if (tr) {
      const li = tr.closest(".syn-n");
      stopRest();
      if (li.classList.contains("syn-shut")) open(li);  // one brace deep
      else anchored(tr, () => fold(li));
      li.querySelector(":scope > .syn-nb .syn-all")?.setAttribute("aria-pressed", "false");
      return;
    }
    const see = ev.target.closest(".syn-sheet a.syn-see");
    if (see) { ev.preventDefault(); history.pushState(null, "", see.getAttribute("href")); reveal(true); }
  });

  // a node reached by a link (a sign such as ♈, or a unit's "where this stands" link): open the way to it, fixed
  const reveal = (smooth) => {
    const target = location.hash && document.getElementById(decodeURIComponent(location.hash.slice(1)));
    const sheet = target?.closest?.(".syn-sheet");
    if (!sheet || !target.classList.contains("syn-n")) return;
    for (let n = target; n; n = n.parentElement.closest(".syn-n")) if (n.classList.contains("syn-shut")) { setShut(n, false); fix(n); }
    settle(sheet);
    target.tabIndex = -1;
    target.focus({ preventScroll: true });
    target.scrollIntoView({ block: "center", behavior: smooth && !reduce.matches ? "smooth" : "auto" });
  };
  window.addEventListener("hashchange", () => reveal(true));
  window.addEventListener("popstate", () => reveal(true));

  document.querySelectorAll(".syn-sheet .syn-all").forEach((b) => { b.hidden = false; });
  // fold what the page marks to start folded, without motion, then fit each sheet and keep it fitted
  for (const sheet of synSheets) {
    sheet.classList.add("syn-still");
    for (const li of sheet.querySelectorAll('[data-fold="shut"]')) setShut(li, true);
    refresh(sheet);
    requestAnimationFrame(() => requestAnimationFrame(() => sheet.classList.remove("syn-still")));
    let t = 0;
    new ResizeObserver(() => { clearTimeout(t); t = setTimeout(() => refresh(sheet), 120); }).observe(sheet);
  }
  document.fonts?.ready.then(() => synSheets.forEach(refresh));
  reveal(false);

  // the synopsis pages: open all, or fold each sheet to its first brace
  const tools = document.querySelector(".syn-tools");
  if (tools) {
    tools.hidden = false;
    tools.addEventListener("click", (ev) => {
      const b = ev.target.closest("button[data-syn]");
      if (!b) return;
      for (const sheet of synSheets) {
        for (const li of sheet.querySelectorAll(".syn-n")) {
          if (!kidsOf(li)) continue;
          li.classList.remove("syn-fixed");
          setShut(li, b.dataset.syn === "close" && !li.classList.contains("syn-root") && li.parentElement.closest(".syn-n")?.classList.contains("syn-root"));
        }
        settle(sheet);
      }
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
// obscure names the names sweep identified (stage 14): {form: {who, probable, label}}
const namesData = Object.assign({}, ...[...document.querySelectorAll("script.names-data")].map((s) => {
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
  if (trig.classList.contains("nm-x")) {
    const n = namesData[trig.dataset.name];
    if (!n) return null;
    box.append(el("p", "pw-h", trig.textContent.replace(/­/g, "")));
    const p = el("p", "pw-t", (n.probable ? "Probably " + n.who : n.who) + " ");
    const pv = el("span", "prov");
    pv.title = n.label;
    pv.setAttribute("aria-label", n.label);
    pv.setAttribute("role", "img");
    pv.tabIndex = 0;
    p.append(pv);
    box.append(p);
    return box;
  }
  if (trig.classList.contains("nm")) {
    const a = authorsData[trig.dataset.author];
    if (!a) return null;
    box.append(el("p", "pw-h", a.name + (a.dates ? `, ${a.dates}` : "")));
    // from the margin, a written-out citation: the work cited there (owner, 2026-11-20: "noting their associated text")
    const cited = trig.classList.contains("cx-a") ? trig.textContent.replace(/­/g, "").trim() : "";
    if (cited && cited !== a.name && !a.name.includes(cited)) box.append(el("p", "pw-c", `Cited here: ${cited}`));
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
// an identified name has no page of its own: a click, Enter or Space opens (and locks) its window
function openName(ev) {
  const t = ev.target.closest?.("a.nm-x");
  if (!t || (ev.type === "keydown" && ev.key !== "Enter" && ev.key !== " ")) return;
  ev.preventDefault();
  openWindow(t).then(() => { const p = pops.find((q) => q.trig === t); if (p?.el) { p.locked = true; p.el.classList.add("locked"); } });
}
document.addEventListener("click", openName);
document.addEventListener("keydown", openName);

// ---------------------------------------------------------------- the front page (stage 4)
// Pointing at a panel of the engraving shows its stanza under the way in (owner, 2026-11-03: T14, R4 B); the last one
// pointed at stays when the pointer leaves the engraving, old Democritus's to begin with (owner, 2026-11-21)
const stanzaBox = document.querySelector(".front-stanza");
if (stanzaBox) {
  // the hint beside the first stanza goes once the reader has pointed at a panel, and stays gone (owner, 2026-11-21)
  const hint = stanzaBox.querySelector(".fs-hint");
  const HINT = "burton-hint-seen";
  try { if (hint && localStorage.getItem(HINT)) hint.hidden = true; } catch { /* private window */ }
  const show = (st) => {
    stanzaBox.querySelectorAll(".fs-st").forEach((d) => { d.hidden = d.dataset.st !== st; });
    if (hint && !hint.hidden) {
      hint.hidden = true;
      try { localStorage.setItem(HINT, "1"); } catch { /* private window */ }
    }
  };
  for (const a of document.querySelectorAll(".front .fs-panel")) {
    a.addEventListener("mouseenter", () => show(a.dataset.st));
    a.addEventListener("focus", () => show(a.dataset.st));
  }
  // a stanza's margin items and the words they hang on light each other, as in the reader; a tap or click holds the
  // pair lit until the next (owner, 2026-11-21)
  const pair = (el) => {
    const id = el.classList.contains("fs-anc") ? el.dataset.for : el.id;
    return [stanzaBox.querySelector(`.fs-anc[data-for="${CSS.escape(id)}"]`), document.getElementById(id)].filter(Boolean);
  };
  let held = null;
  for (const el of stanzaBox.querySelectorAll(".fs-anc, .fs-mn")) {
    el.addEventListener("mouseenter", () => pair(el).forEach((x) => x.classList.add("hot")));
    el.addEventListener("mouseleave", () => pair(el).forEach((x) => { if (!held?.includes(x)) x.classList.remove("hot"); }));
    el.addEventListener("click", (ev) => {
      if (ev.target.closest("a[href]")) return;  // a link in a note keeps its own work
      const p = pair(el);
      const same = held && held[0] === p[0];
      held?.forEach((x) => x.classList.remove("hot", "pinned"));
      held = same ? null : p;
      held?.forEach((x) => x.classList.add("hot", "pinned"));
    });
  }
}
// The engraving's title panel (and only it) magnified while the pointer rests on it, within the engraving's own
// bounds, until the pointer leaves the engraving (owner, 2026-11-21)
const frontMap = document.querySelector(".front .fs-map");
const titleZone = frontMap?.querySelector(".fs-title");
if (frontMap && titleZone) {
  titleZone.addEventListener("mouseenter", () => frontMap.classList.add("fs-zoomed"));
  frontMap.addEventListener("mouseleave", () => frontMap.classList.remove("fs-zoomed"));
}
// the front page's specimen: each sign lights its pair (Latin and its translation, a note's letter and the note, §
// and the citation written out) on pointing, a tap or click holds it, as in the reader; a tap on a name opens who
// it was (owner, 2026-11-21)
const spec = document.querySelector(".sp");
if (spec) {
  const mates = (el) => [...spec.querySelectorAll(`[data-k="${el.dataset.k}"]`)];
  let held = null;
  for (const el of spec.querySelectorAll("[data-k]")) {
    el.addEventListener("mouseenter", () => mates(el).forEach((x) => x.classList.add("hot")));
    el.addEventListener("mouseleave", () => mates(el).forEach((x) => { if (held !== el.dataset.k) x.classList.remove("hot"); }));
    el.addEventListener("click", (ev) => {
      if (ev.target.closest(".sp-nm")) return;
      spec.querySelectorAll(".hot, .pinned").forEach((x) => x.classList.remove("hot", "pinned"));
      held = held === el.dataset.k ? null : el.dataset.k;
      if (held) mates(el).forEach((x) => x.classList.add("hot", "pinned"));
    });
  }
  for (const nm of spec.querySelectorAll(".sp-nm")) {
    nm.addEventListener("click", (ev) => { ev.stopPropagation(); nm.classList.toggle("open"); });
  }
}
// the front page's box, shortened while a Partition's braces are open, opens again on asking (owner, 2026-11-21)
const fiExpand = document.querySelector(".fi-expand");
fiExpand?.addEventListener("click", () => {
  const box = fiExpand.closest(".front-info");
  const full = box.classList.toggle("fi-full");
  fiExpand.setAttribute("aria-expanded", String(full));
  fiExpand.textContent = full ? "Read less" : "Read more";
});
// the front page's contents start folded (owner, 2026-11-20); a link to a place in them opens them
const frontContents = document.querySelector(".front-contents");
if (frontContents) {
  const openTo = () => {
    const t = location.hash && document.getElementById(decodeURIComponent(location.hash.slice(1)));
    if (t && frontContents.contains(t)) { frontContents.open = true; t.scrollIntoView(); }
  };
  openTo();
  window.addEventListener("hashchange", openTo);
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
