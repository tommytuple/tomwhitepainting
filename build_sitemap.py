#!/usr/bin/env python3
"""Regenerate sitemap.xml from the HTML files in this repo.

Every .html file becomes one URL, using its canonical link if it has one so
the sitemap and the pages can never disagree. Run it after adding a page:

    python3 build_sitemap.py
"""

import datetime
import pathlib
import re
import subprocess

SITE = "https://tomwhitepainter.co.uk"
ROOT = pathlib.Path(__file__).parent

# Pages nearer the top of the site get the higher priority. These are hints
# rather than instructions; Google mostly ignores them, but Bing still reads
# them and they cost nothing.
PRIORITY = {
    "/": "1.0",
    "/explore-paint-colours/": "0.9",
    "/contact.html": "0.8",
}


def last_modified(path: pathlib.Path) -> str:
    """The file's last commit date, falling back to its mtime when the file
    is new and not yet committed."""
    try:
        out = subprocess.run(
            ["git", "log", "-1", "--format=%cs", "--", str(path)],
            cwd=ROOT, capture_output=True, text=True, timeout=10,
        )
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return datetime.date.fromtimestamp(path.stat().st_mtime).isoformat()


def url_for(path: pathlib.Path) -> str:
    """Prefer the page's own canonical tag, so there is one source of truth."""
    canonical = re.search(
        r'<link\s+rel="canonical"\s+href="([^"]+)"', path.read_text()
    )
    if canonical:
        return canonical.group(1)

    rel = path.relative_to(ROOT).as_posix()
    rel = re.sub(r"(^|/)index\.html$", r"\1", rel)
    return f"{SITE}/{rel}"


def main() -> None:
    pages = sorted(
        p for p in ROOT.rglob("*.html")
        if ".git" not in p.parts and "node_modules" not in p.parts
    )

    entries = []
    for page in pages:
        loc = url_for(page)
        priority = PRIORITY.get(loc[len(SITE):], "0.7")
        entries.append(
            "  <url>\n"
            f"    <loc>{loc}</loc>\n"
            f"    <lastmod>{last_modified(page)}</lastmod>\n"
            f"    <priority>{priority}</priority>\n"
            "  </url>"
        )

    (ROOT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(entries)
        + "\n</urlset>\n"
    )
    print(f"sitemap.xml: {len(entries)} urls")


if __name__ == "__main__":
    main()
