// Full-text search (M8). The index (assets/search-index.json) is fetched on the first search and
// kept by the service worker, so search works offline. Matching ignores case, accents and the æ/œ
// ligatures; the text shown is the index's, unaltered, with the matched words marked.

const form = document.querySelector(".search-form");
const input = document.getElementById("q");
const status = document.querySelector(".search-status");
const list = document.querySelector(".search-results");
const indexUrl = new URL("search-index.json", import.meta.url);
const siteRoot = new URL("..", import.meta.url);
const SHOW = 100; // results listed at a time
const LANG = { la: "Latin", grc: "Greek", it: "Italian", fr: "French", es: "Spanish", de: "German", nl: "Dutch",
  he: "Hebrew", ar: "Arabic", enm: "Middle English" };
const SCRIPT = [[/[Ͱ-Ͽἀ-῿]/u, "grc"], [/[֐-׿]/u, "he"], [/[؀-ۿ]/u, "ar"]];

let index = null;
let norms = null; // normalised text of each document, built once

// One character at a time, so each normalised offset maps back to the original text.
function normChar(c) {
  const lower = c.toLowerCase();
  if (lower === "æ") return "ae";
  if (lower === "œ") return "oe";
  if (lower === "ς") return "σ";
  if (c === "’" || c === "‘" || c === "ʼ") return "'";
  if (c === "­") return "";
  return lower.normalize("NFD").replace(/\p{M}/gu, "");
}
function normalise(s) {
  let out = "";
  for (const c of s) out += normChar(c);
  return out;
}
// The normalised text and, for each of its code units, the offset of the original character.
function mapped(s) {
  let out = "";
  const map = [];
  let i = 0;
  for (const c of s) {
    const n = normChar(c);
    for (let k = 0; k < n.length; k++) map.push(i);
    out += n;
    i += c.length;
  }
  map.push(i);
  return [out, map];
}

function terms(q) {
  const out = [];
  const re = /"([^"]+)"|“([^”]+)”|(\S+)/g;
  let m;
  while ((m = re.exec(q))) {
    const t = normalise((m[1] || m[2] || m[3]).replace(/^[^\p{L}\p{N}]+|[^\p{L}\p{N}]+$/gu, "")).trim();
    if (t) out.push(t.replace(/\s+/g, " "));
  }
  return out;
}

async function load() {
  if (index) return;
  status.textContent = "Loading the search index…";
  const res = await fetch(indexUrl);
  if (!res.ok) throw new Error(`index: HTTP ${res.status}`);
  index = await res.json();
  norms = index.docs.map((d) => normalise(d[3]).replace(/\s+/g, " "));
}

function esc(s) {
  return s.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
}
// Wrap runs of Greek, Hebrew or Arabic in an element with the right lang (CLAUDE.md V4).
function tagScripts(s) {
  let out = "";
  let run = "", lang = null;
  const flush = () => {
    if (!run) return;
    out += lang ? `<span lang="${lang}">${esc(run)}</span>` : esc(run);
    run = "";
  };
  for (const c of s) {
    const l = SCRIPT.find(([re]) => re.test(c))?.[1] || (lang && /[\s\p{M}\p{P}]/u.test(c) ? lang : null);
    if (l !== lang) { flush(); lang = l; }
    run += c;
  }
  flush();
  return out;
}

// A window of the text around the first match, with every match marked.
function snippet(text, ts) {
  const [n, map] = mapped(text.replace(/\s+/g, " "));
  const flat = text.replace(/\s+/g, " ");
  const hits = [];
  for (const t of ts) {
    let p = n.indexOf(t);
    while (p >= 0) { hits.push([map[p], map[p + t.length]]); p = n.indexOf(t, p + t.length); }
  }
  hits.sort((a, b) => a[0] - b[0]);
  const first = hits.length ? hits[0][0] : 0;
  let start = Math.max(0, first - 120), end = Math.min(flat.length, first + 280);
  if (start > 0) start = flat.indexOf(" ", start) + 1 || start;
  if (end < flat.length) end = flat.lastIndexOf(" ", end) > first ? flat.lastIndexOf(" ", end) : end;
  let out = start > 0 ? "… " : "", pos = start;
  for (const [a, b] of hits) {
    if (a < pos || b > end) continue;
    out += tagScripts(flat.slice(pos, a)) + `<mark>${tagScripts(flat.slice(a, b))}</mark>`;
    pos = b;
  }
  out += tagScripts(flat.slice(pos, end)) + (end < flat.length ? " …" : "");
  return out;
}

function render(q, ts, scope, found, shown) {
  list.replaceChildren();
  const html = [];
  for (const i of found.slice(0, shown)) {
    const d = index.docs[i];
    const [unit, title] = index.units[d[0]];
    const kind = index.kinds[d[1]];
    const href = new URL(`${unit}/#${d[2]}`, siteRoot).href;
    let tag = kind === "note" ? '<span class="sr-kind">Sidenote</span>' : "";
    if (kind === "translation") {
      const [lang, orig] = index.origs[d[4]];
      const from = LANG[lang] ? ` from ${LANG[lang]}` : "";
      const short = orig.length > 160 ? `${orig.slice(0, orig.lastIndexOf(" ", 160))} …` : orig;
      tag = `<span class="sr-kind">Translation${esc(from)} · ${esc(index.labels[d[5]])}</span>` +
        `<span class="sr-orig"${lang ? ` lang="${esc(lang)}"` : ""}>${esc(short)}</span>`;
    }
    const lang = kind === "translation" ? ' lang="en"' : "";
    html.push(`<li class="sr sr-${kind}"><a href="${esc(href)}">${esc(title)}</a>${tag}` +
      `<p class="sr-text"${lang}>${snippet(d[3], ts)}</p></li>`);
  }
  list.innerHTML = html.join("");
  const where = scope.map((k) => ({ text: "Burton’s text", note: "sidenotes", translation: "translations" })[k]).join(", ");
  const units = new Set(found.map((i) => index.docs[i][0])).size;
  status.textContent = found.length
    ? `${found.length.toLocaleString("en")} passage${found.length === 1 ? "" : "s"} in ${units} page${units === 1 ? "" : "s"} (${where})` +
      (found.length > shown ? `; showing the first ${shown}.` : ".")
    : `Nothing found for ${q} in ${where}.`;
  if (found.length > shown) {
    const li = document.createElement("li");
    li.className = "sr-more";
    const b = document.createElement("button");
    b.type = "button";
    b.textContent = `Show ${Math.min(SHOW, found.length - shown)} more`;
    b.addEventListener("click", () => {
      const next = list.children.length - 1;
      render(q, ts, scope, found, shown + SHOW);
      list.children[next]?.querySelector("a")?.focus();
    });
    li.append(b);
    list.append(li);
  }
}

async function run(q, scope) {
  const ts = terms(q);
  if (!ts.length) { list.replaceChildren(); status.textContent = "Type a word or a phrase."; return; }
  try {
    await load();
  } catch (e) {
    status.textContent = `The search index could not be loaded (${e.message}).`;
    return;
  }
  const kinds = new Set(scope.map((k) => index.kinds.indexOf(k)));
  const found = [];
  for (let i = 0; i < norms.length; i++) {
    if (!kinds.has(index.docs[i][1])) continue;
    const n = norms[i];
    if (ts.every((t) => n.includes(t))) found.push(i);
  }
  render(`“${q}”`, ts, scope, found, SHOW);
}

function scopeOf() {
  return [...form.querySelectorAll('input[name="in"]:checked')].map((x) => x.value);
}

form.addEventListener("submit", (ev) => {
  ev.preventDefault();
  const q = input.value.trim();
  const scope = scopeOf();
  const params = new URLSearchParams({ q });
  for (const s of scope) params.append("in", s);
  history.replaceState(null, "", `?${params}`);
  if (!scope.length) { status.textContent = "Choose at least one of Burton’s text, sidenotes or translations."; return; }
  run(q, scope);
});

// A search reached by URL (?q=…&in=…), e.g. from the back button.
const params = new URLSearchParams(location.search);
if (params.get("q")) {
  input.value = params.get("q");
  const scope = params.getAll("in");
  if (scope.length) for (const x of form.querySelectorAll('input[name="in"]')) x.checked = scope.includes(x.value);
  run(input.value, scopeOf());
} else {
  status.textContent = "";
}
