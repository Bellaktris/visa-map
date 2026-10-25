#!/usr/bin/env python3
"""Emit two builds from template.html.

  visa-map.html  everything inlined — one file you can email or open offline
  index.html     assets referenced from vendor/ and data/ — for GitHub Pages, where
                 d3 and the world atlas are ~320 KB gzipped that never change and
                 should stay in the browser cache across data updates
"""
import pathlib

ROOT = pathlib.Path(__file__).parent
DATA = ROOT / "data"
VENDOR = ROOT / "vendor"

# marker -> the file whose contents replace it in the single-file build
SLOTS = {
    "/*__D3__*/": VENDOR / "d3.min.js",
    "/*__TOPOJSON__*/": VENDOR / "topojson-client.min.js",
    "/*__WORLD__*/": VENDOR / "countries-50m.json",
    "/*__VISA__*/": DATA / "visa.json",
}

template = (ROOT / "template.html").read_text(encoding="utf-8")
for marker in SLOTS:
    assert marker in template, f"template is missing {marker}"


def read(path):
    # inside <script type="application/json"> the only sequence that can break out is "</"
    text = path.read_text(encoding="utf-8")
    return text.replace("</", "<\\/") if path.suffix == ".json" else text


# ── single file ──────────────────────────────────────────────────────────────
inlined = template
for marker, src in SLOTS.items():
    inlined = inlined.replace(marker, read(src))
single = ROOT / "visa-map.html"
single.write_text(inlined, encoding="utf-8")

# ── split for Pages ──────────────────────────────────────────────────────────
split = template
split = split.replace("<script>/*__D3__*/</script>", '<script src="vendor/d3.min.js"></script>')
split = split.replace("<script>/*__TOPOJSON__*/</script>",
                      '<script src="vendor/topojson-client.min.js"></script>')
# the app reads both blobs out of the DOM, so fetch them and inject before booting
split = split.replace(
    '<script id="world" type="application/json">/*__WORLD__*/</script>\n'
    '<script id="visa" type="application/json">/*__VISA__*/</script>\n'
    "<script>\n(function () {",
    '<script id="world" type="application/json"></script>\n'
    '<script id="visa" type="application/json"></script>\n'
    "<script>\n"
    "Promise.all([\n"
    '  fetch("vendor/countries-50m.json").then(r => r.text()),\n'
    '  fetch("data/visa.json").then(r => r.text()),\n'
    "]).then(([world, visa]) => {\n"
    '  document.getElementById("world").textContent = world;\n'
    '  document.getElementById("visa").textContent = visa;\n'
    "  boot();\n"
    '}).catch(e => { document.getElementById("boot-error").hidden = false; throw e; });\n'
    "function boot() {\n(function () {")
split = split.replace("  paint();\n})();\n</script>", "  paint();\n})();\n}\n</script>")
split = split.replace('<div class="spot" id="spotlight"></div>',
                      '<p class="warn" id="boot-error" hidden><strong>Could not load the map data.</strong> '
                      "Open this page over http(s), not as a local file — browsers block "
                      "<code>fetch</code> from <code>file://</code>.</p>\n\n"
                      '  <div class="spot" id="spotlight"></div>')
assert "/*__WORLD__*/" not in split and "function boot()" in split, "split rewrite failed"

index = ROOT / "index.html"
index.write_text(split, encoding="utf-8")

for f in (single, index):
    print(f"wrote {f.name:16s} {f.stat().st_size / 1024:6.0f} KB")
