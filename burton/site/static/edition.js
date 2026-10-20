// Reading options, notes and translation behaviour. Progressive enhancement: the text and
// Burton's notes are readable without this script.

const KEY = "burton-settings";
const root = new URL("..", import.meta.url);
const body = document.body;
const narrow = window.matchMedia("(max-width: 1099px)");

function load() {
  try { return JSON.parse(localStorage.getItem(KEY) || "{}"); } catch { return {}; }
}
function save(s) {
  try { localStorage.setItem(KEY, JSON.stringify(s)); } catch { /* private window: settings last for this page only */ }
}

const settings = Object.assign({ mode: "gloss", theme: "auto", gowland: false, pages: false }, load());

function apply() {
  body.classList.remove("mode-gloss", "mode-interlinear", "mode-english");
  body.classList.add(`mode-${settings.mode}`);
  if (settings.theme === "auto") delete document.documentElement.dataset.theme;
  else document.documentElement.dataset.theme = settings.theme;
  body.classList.toggle("show-gowland", !!settings.gowland);
  body.classList.toggle("show-pages", !!settings.pages);
  document.querySelectorAll(".fp.show-orig").forEach((f) => f.classList.remove("show-orig"));
}

// ---------------------------------------------------------------- settings panel
const panel = document.getElementById("settings");
const toggle = document.querySelector(".settings-toggle");
if (panel && toggle) {
  toggle.addEventListener("click", () => {
    const open = panel.hidden;
    panel.hidden = !open;
    toggle.setAttribute("aria-expanded", String(open));
  });
  for (const input of panel.querySelectorAll("input")) {
    if (input.type === "radio") input.checked = settings[input.name] === input.value;
    else input.checked = !!settings[input.name];
    input.addEventListener("change", () => {
      settings[input.name] = input.type === "radio" ? input.value : input.checked;
      save(settings);
      apply();
    });
  }
}
apply();

// ---------------------------------------------------------------- Burton's sidenotes
let openNote = null;
function closeNote(focusMarker) {
  if (!openNote) return;
  const { note, marker } = openNote;
  note.classList.remove("open");
  marker.setAttribute("aria-expanded", "false");
  if (focusMarker) marker.focus();
  openNote = null;
}
for (const marker of document.querySelectorAll("a.nref")) {
  const note = document.getElementById(marker.getAttribute("href").slice(1));
  if (!note) continue;
  marker.setAttribute("aria-controls", note.id);
  marker.setAttribute("aria-expanded", "false");
  marker.addEventListener("click", (ev) => {
    ev.preventDefault();
    if (narrow.matches) {
      const isOpen = openNote && openNote.note === note;
      closeNote(false);
      if (!isOpen) {
        note.classList.add("open");
        marker.setAttribute("aria-expanded", "true");
        openNote = { note, marker };
      }
    } else {
      note.classList.add("flash");
      setTimeout(() => note.classList.remove("flash"), 1200);
    }
  });
}
document.addEventListener("keydown", (ev) => {
  if (ev.key === "Escape") {
    closeNote(true);
    document.querySelectorAll(".fp.pinned").forEach((f) => f.classList.remove("pinned"));
  }
});

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

// ---------------------------------------------------------------- offline (installable app)
if ("serviceWorker" in navigator && location.protocol.startsWith("http")) {
  navigator.serviceWorker.register(new URL("sw.js", root)).catch(() => {});
}
