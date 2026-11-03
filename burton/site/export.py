"""`burton export-artifact`: a built site, adjusted for hosting as a claude.ai Artifact -> site/artifact-<profile>/.

The Artifact host serves files exactly as named and wraps the main page in its own document skeleton, so:
* every local link or source that names a directory ("1.1.1.2/", "../", "./") names its index.html;
* the main page (index.html) keeps its head's title, styles and scripts and drops its own html/head/body
  wrappers; a first script restores the body's classes and the page language;
* the service worker is left out (the host does not run one; the script already tolerates its absence).
The built site itself is not changed. Owner, 2026-11-03: the private build, for the owner only, not shared.
"""

import re
import shutil

from .. import paths

LINK = re.compile(r'(\s(?:href|src)=")([^"]*)(")')


def _fix(url: str) -> str:
    if re.match(r"^[a-z]+:|^#|^//", url) or url == "":
        return url
    path, hash_, frag = url.partition("#")
    if path == "" or path.endswith("/"):
        path += "index.html"
    elif path in (".", ".."):
        path += "/index.html"
    return path + hash_ + frag


def _main_page(html: str) -> str:
    head = re.search(r"<head>(.*?)</head>", html, re.S).group(1)
    body_tag = re.search(r"<body([^>]*)>", html)
    body = html[body_tag.end():html.rindex("</body>")]
    cls = re.search(r'class="([^"]*)"', body_tag.group(1))
    head = re.sub(r'<meta charset="[^"]*">\s*|<meta name="viewport"[^>]*>\s*', "", head)
    head = re.sub(r"<title>.*?</title>", "<title>The Anatomy of Melancholy</title>", head, flags=re.S)
    boot = (f'<script>document.documentElement.lang="en";'
            f'document.body.className={cls.group(1)!r};</script>\n' if cls else "")
    return head.strip() + "\n" + boot + body.strip() + "\n"


def export(profile: str) -> dict:
    src, out = paths.SITE / profile, paths.SITE / f"artifact-{profile}"
    if not (src / "index.html").exists():
        raise SystemExit(f"site/{profile} is not built: run `burton build --all --profile {profile}`")
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(src, out, ignore=shutil.ignore_patterns("sw.js"))
    n_links = 0
    for f in out.rglob("*.html"):
        text = f.read_text(encoding="utf-8")

        def rep(m):
            nonlocal n_links
            new = _fix(m.group(2))
            n_links += new != m.group(2)
            return m.group(1) + new + m.group(3)

        text = LINK.sub(rep, text)
        if f == out / "index.html":
            text = _main_page(text)
        f.write_text(text, encoding="utf-8", newline="\n")
    js = out / "assets" / "search.js"
    js.write_text(js.read_text(encoding="utf-8").replace("`${unit}/#${d[2]}`", "`${unit}/index.html#${d[2]}`"),
                  encoding="utf-8", newline="\n")
    files = sorted(p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file())
    return {"dir": out.as_posix(), "files": len(files), "links_rewritten": n_links,
            "bytes": sum((out / f).stat().st_size for f in files)}
