#!/usr/bin/env python3
"""Archive CrazyGames developer previews: build, cover art, video and metadata per game."""

import html
import json
import re
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

import brotli

ROOT = Path(__file__).parent
UA = {"User-Agent": "Mozilla/5.0"}
EXT = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/gif": ".gif"}


def fetch(url):
    req = urllib.request.Request(urllib.parse.quote(url, safe=":/?&=%"), headers=UA)
    with urllib.request.urlopen(req) as r:
        data = r.read()
        # The CDN sometimes serves .br files still compressed, sometimes already decoded
        if r.headers.get("Content-Encoding") == "br":
            data = brotli.decompress(data)
        return data, r.headers.get_content_type()


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    print(f"  {path.relative_to(ROOT)} ({len(data) / 1e6:.1f} MB)")


def to_markdown(s):
    s = re.sub(r"<h\d[^>]*>(.*?)</h\d>", r"\n## \1\n", s or "")
    s = re.sub(r"<li[^>]*>\s*", "- ", s)
    s = re.sub(r"</li>\s*", "\n", s).replace("</p>", "\n\n")
    s = re.sub(r"<[^>]+>|^[ \t]+", "", s, flags=re.M)
    return re.sub(r"\n{3,}", "\n\n", html.unescape(s)).strip()


def modern_build(g, out):
    """Unity 2020+: loader.js plus .br files, saved decompressed so they load without server headers."""
    cfg = g["loaderConfig"]
    opts = cfg["unityConfigOptions"]
    loader = cfg["unityLoaderUrl"].rsplit("/", 1)[1]
    save(out / "Build" / loader, fetch(cfg["unityLoaderUrl"])[0])
    # devicePixelRatio 1: the index page already renders games at screen size.
    local = {"companyName": g["developer"], "productName": g["name"], "devicePixelRatio": 1}
    for key, url in opts.items():
        name = url.rsplit("/", 1)[1].removesuffix(".br")
        save(out / "Build" / name, fetch(url)[0])
        local[key] = f"Build/{name}"
    return f"""<canvas id="unity-canvas"></canvas>
<script src="Build/{loader}"></script>
<script>
  createUnityInstance(document.querySelector("#unity-canvas"), {json.dumps(local)});
</script>"""


def legacy_build(g, out):
    """Unity 5.6-2019: UnityLoader.js plus a Build JSON listing .unityweb files (decompressed by the loader)."""
    cfg = g["loaderConfig"]
    json_url = cfg["moduleJsonUrl"]
    base, json_name = json_url.rsplit("/", 1)
    raw = fetch(json_url)[0]
    save(out / "Build" / json_name, raw)
    for key, name in json.loads(raw).items():
        if key.endswith("Url") and isinstance(name, str):
            save(out / "Build" / name, fetch(f"{base}/{name}")[0])
    save(out / "Build" / "UnityLoader.js", fetch(cfg["unityLoaderUrl"])[0])
    return f"""<div id="unity-container"></div>
<script src="Build/UnityLoader.js"></script>
<script>
  window.unityInstance = UnityLoader.instantiate("unity-container", "Build/{json_name}");
</script>"""


def archive(preview_url):
    page = fetch(preview_url)[0].decode()
    data = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', page, re.S).group(1)
    g = json.loads(data)["props"]["pageProps"]["game"]
    out = ROOT / g["slug"]
    print(f"\n{g['name']}")

    for ratio, path in (g.get("covers") or {"16x9": g["cover"]}).items():
        img, ctype = fetch(f"https://imgs.crazygames.com/{path}")
        save(out / "images" / f"{g['slug']}-{ratio}{EXT.get(ctype, '.jpg')}", img)

    videos = g.get("videos") or {}
    for key in ("original", "portraitOriginal"):
        if videos.get(key):
            name = videos[key].rsplit("/", 1)[1]
            if key == "portraitOriginal":
                name = name.replace(".mp4", "-portrait.mp4")
            save(out / "video" / name, fetch(f"https://videos.crazygames.com/{videos[key]}")[0])

    build = modern_build if "unityConfigOptions" in g["loaderConfig"] else legacy_build
    body = build(g, out / "game")
    # Local replacements for downloaded files (Cat Car runs with its original Unity 2019 loader).
    if (overrides := ROOT / "overrides" / g["slug"]).is_dir():
        shutil.copytree(overrides, out, dirs_exist_ok=True)
    (out / "game" / "index.html").write_text(f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{html.escape(g['name'])}</title>
<link rel="stylesheet" href="../../../game.css">
</head>
<body>
<script src="../../crazygames-sdk.js"></script>
{body}
</body>
</html>
""")

    (out / "info.json").write_text(json.dumps(g, indent=2, ensure_ascii=False))
    links = [f"- {label}: {g[k]}" for label, k in
             (("Google Play", "playStoreUrl"), ("App Store", "appStoreUrl"), ("Steam", "steamStoreUrl"),
              ("CrazyGames", "desktopUrl")) if g.get(k)]
    (out / "README.md").write_text(f"""# {g['name']}

by {g['developer']} · engine: {g.get('loaderTypeLabel') or g['loaderType']} · added {g.get('addedOn')} · last update {g.get('lastFileUpdatedOn') or 'unknown'}
CrazyGames rating: {g.get('rating')} ({g.get('upvotes')} up / {g.get('downvotes')} down)

## Description

{to_markdown(g.get('descriptionFirst'))}

{to_markdown(g.get('descriptionRest'))}

{to_markdown(g.get('controls'))}

## Links

{chr(10).join(links)}
""")


if __name__ == "__main__":
    urls = sys.argv[1:] or (ROOT / "links.txt").read_text().split()
    for u in urls:
        archive(u)
    # Format the generated files; .prettierignore keeps the original builds untouched.
    subprocess.run(["npx", "prettier", "--write", "."], cwd=ROOT.parent, check=True)
