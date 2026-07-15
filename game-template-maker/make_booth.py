#!/usr/bin/env python3
"""
Game Template Maker  —  photo-booth edition
===========================================

Recreate the GTAD photo-booth "game" for any brand from a single JSON config.
Change the colour scheme, web info, socials and branding in one file, run this,
and get a complete, ready-to-deploy site folder. Same proven formula every time.

    python3 make_booth.py brands/gtad.json
    python3 make_booth.py brands/my-new-brand.json -o build/my-brand

Standard-library only. No install, no dependencies.

See README.md for the full config reference, or booth_config.schema.json for the
machine-readable schema. brands/gtad.json is the original show, as a worked example.
"""
from __future__ import annotations
import argparse, base64, json, os, sys

# Resource base: the source dir normally, or the PyInstaller bundle dir when frozen
# into a desktop app (Booth Studio). Lets the same code find templates/ + brands/
# whether run as a script or a packaged executable.
if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    HERE = sys._MEIPASS
else:
    HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATES = os.path.join(HERE, "templates")
BRANDS = os.path.join(HERE, "brands")

# ---------------------------------------------------------------------------
# colour helpers
# ---------------------------------------------------------------------------
def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) != 6:
        raise ValueError(f"bad hex colour: #{h}")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)

def _rgb_str(h: str) -> str:
    r, g, b = _hex_to_rgb(h)
    return f"{r},{g},{b}"

def _darken(h: str, f: float) -> str:
    r, g, b = _hex_to_rgb(h)
    return "#{:02x}{:02x}{:02x}".format(
        max(0, min(255, round(r * f))),
        max(0, min(255, round(g * f))),
        max(0, min(255, round(b * f))),
    )

# ---------------------------------------------------------------------------
# defaults  (house style + anything the operator usually doesn't need to touch)
# Identity fields are intentionally NOT defaulted — see REQUIRED below.
# ---------------------------------------------------------------------------
DEFAULT_COLORS = {
    "bg": "#0a0a0f",
    "primary": "#ff1e6c",
    "primaryBright": "#ff4f8b",
    "secondary": "#16e0ff",
    "accent": "#ffc23d",
    "ink": "#f5f5fa",
    "dim": "#9aa0b5",
}

REQUIRED = [
    ("brand", "name"),
    ("brand", "short"),
    ("brand", "lineOne"),
    ("brand", "lineTwo"),
    ("web", "storagePrefix"),
]

def _get(cfg, *path, default=None):
    cur = cfg
    for p in path:
        if not isinstance(cur, dict) or p not in cur:
            return default
        cur = cur[p]
    return cur

def _slug(s: str) -> str:
    out = "".join(c.lower() if c.isalnum() else "-" for c in (s or ""))
    while "--" in out:
        out = out.replace("--", "-")
    return out.strip("-")

# ---------------------------------------------------------------------------
# build the flat token table the templates expect
# ---------------------------------------------------------------------------
def build_tokens(cfg: dict, config_dir: str) -> dict:
    # ---- validate identity ----
    missing = [".".join(p) for p in REQUIRED if _get(cfg, *p) in (None, "")]
    if missing:
        raise SystemExit("Config is missing required fields: " + ", ".join(missing))

    brand = cfg.get("brand", {})
    colors = {**DEFAULT_COLORS, **cfg.get("colors", {})}
    web = cfg.get("web", {})
    soc = cfg.get("socials", {})

    prefix = web["storagePrefix"]
    short = brand["short"]
    name = brand["name"]

    netlify_name = web.get("netlifyName", prefix)
    primary_domain = web.get("primaryDomain", f"{netlify_name}.netlify.app")
    root_domain = web.get("rootDomain", primary_domain)
    bucket_name = web.get("bucketName", f"{prefix}-booth-inbox")
    project_slug = web.get("projectSlug", f"{prefix}-photobooth")
    cors_rule = web.get("corsRuleName", f"{_slug(prefix).replace('-', '')}Booth")

    cors_origins = web.get("corsOrigins") or [
        f"https://{netlify_name}.netlify.app",
        f"https://{primary_domain}",
    ]
    if root_domain not in (primary_domain, "") and f"https://{root_domain}" not in cors_origins:
        cors_origins = cors_origins + [f"https://{root_domain}"]
    cors_js = "[" + ", ".join(f"'{o}'" for o in cors_origins) + "]"

    # instagram handle: explicit, else last path segment of the IG url
    ig = soc.get("instagram", "#")
    ig_handle = soc.get("igHandle") or _slug(ig.rstrip("/").split("/")[-1].lstrip("@")) or prefix

    # ---- logo -> embedded data URI (optional; text lockup is the fallback) ----
    logo_uri = "null"
    logo_path = brand.get("logo")
    if logo_path:
        p = logo_path if os.path.isabs(logo_path) else os.path.join(config_dir, logo_path)
        if not os.path.exists(p):
            raise SystemExit(f"brand.logo points to a missing file: {p}")
        ext = os.path.splitext(p)[1].lstrip(".").lower() or "png"
        mime = {"jpg": "jpeg", "jpe": "jpeg"}.get(ext, ext)
        with open(p, "rb") as f:
            data = base64.b64encode(f.read()).decode("ascii")
        logo_uri = f"'data:image/{mime};base64,{data}'"

    # ---- show data (optional) -> powers the crew card + handler console ----
    # Accept an inline object or a path (relative to the config file) under "show".
    show = cfg.get("show")
    if isinstance(show, str):
        sp = show if os.path.isabs(show) else os.path.join(config_dir, show)
        if not os.path.exists(sp):
            raise SystemExit(f"show points to a missing file: {sp}")
        with open(sp, encoding="utf-8") as f:
            show = json.load(f)
    if not isinstance(show, dict):
        show = {}
    # embed safely: "</" broken so the blob can't close the <script> early
    show_json = json.dumps(show, ensure_ascii=False).replace("</", "<\\/")

    tokens = {
        # brand / identity
        "brand.name": name,
        "brand.short": short,
        "brand.lineOne": brand["lineOne"],
        "brand.lineTwo": brand["lineTwo"],
        "brand.kicker": brand.get("kicker", "★ Presents ★"),
        "brand.tagline": brand.get("tagline", "Tap below to strike a pose."),
        "brand.followLabel": brand.get("followLabel", "Follow the movement"),
        "brand.hashtag": brand.get("hashtag", "#" + "".join(w.capitalize() for w in name.split())),
        "brand.galleryCta": brand.get("galleryCta", f"Add to {short} Gallery"),
        "brand.galleryDone": brand.get("galleryDone", "Added to Gallery"),
        "brand.legal": brand.get("legal", ""),
        # colours (base)
        "colors.bg": colors["bg"],
        "colors.primary": colors["primary"],
        "colors.primaryBright": colors["primaryBright"],
        "colors.secondary": colors["secondary"],
        "colors.accent": colors["accent"],
        "colors.ink": colors["ink"],
        "colors.dim": colors["dim"],
        # colours (derived)
        "colors.primaryRgb": _rgb_str(colors["primary"]),
        "colors.secondaryRgb": _rgb_str(colors["secondary"]),
        "colors.bgRgb": _rgb_str(colors["bg"]),
        "colors.primaryDeep": _darken(colors["primary"], 0.47),
        "colors.secondaryDeep": _darken(colors["secondary"], 0.82),
        "colors.secondaryDeepest": _darken(colors["secondary"], 0.28),
        "colors.onSecondary": _darken(colors["secondary"], 0.16),
        # socials
        "socials.instagram": soc.get("instagram", "#"),
        "socials.facebook": soc.get("facebook", "#"),
        "socials.tiktok": soc.get("tiktok", "#"),
        "socials.igHandle": ig_handle,
        # web / deploy
        "web.storagePrefix": prefix,
        "web.primaryDomain": primary_domain,
        "web.rootDomain": root_domain,
        "web.netlifyName": netlify_name,
        "web.bucketName": bucket_name,
        "web.projectSlug": project_slug,
        "web.corsRuleName": cors_rule,
        "web.corsOriginsJs": cors_js,
        # logo
        "logo_data_uri": logo_uri,
        # show (crew card + handler console)
        "show_json": show_json,
        # internal flag (not a template token): whether show-driven modules apply
        "_has_show": bool(show),
    }
    return tokens

# ---------------------------------------------------------------------------
# render
# ---------------------------------------------------------------------------
def render(text: str, tokens: dict, rel: str) -> str:
    import re
    def repl(m):
        key = m.group(1)
        if key not in tokens:
            raise SystemExit(f"Unknown template token {{{{{key}}}}} in {rel}")
        return str(tokens[key])
    return re.sub(r"\{\{([a-zA-Z0-9_.]+)\}\}", repl, text)

TEXT_EXT = {".html", ".js", ".toml", ".md", ".txt", ".json", ".css"}

# Core generator. Takes an in-memory config dict so it can be driven by the CLI or
# the desktop app (Booth Studio). `config_dir` is where relative logo/show paths
# resolve from. Returns a summary dict; raises SystemExit on bad input.
def generate_from_cfg(cfg: dict, out_dir: str, config_dir: str = ".") -> dict:
    tokens = build_tokens(cfg, config_dir)

    if not os.path.isdir(TEMPLATES):
        raise SystemExit(f"templates/ not found ({TEMPLATES})")

    # Show-driven modules only make sense when a show is supplied.
    SHOW_ONLY = {"crew.html", "handler.html"}
    has_show = tokens.get("_has_show")

    os.makedirs(out_dir, exist_ok=True)
    count = 0
    skipped = []
    for root, _dirs, files in os.walk(TEMPLATES):
        for fn in files:
            if fn in SHOW_ONLY and not has_show:
                skipped.append(fn)
                continue
            src = os.path.join(root, fn)
            rel = os.path.relpath(src, TEMPLATES)
            dst = os.path.join(out_dir, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            ext = os.path.splitext(fn)[1].lower()
            if ext in TEXT_EXT:
                with open(src, encoding="utf-8") as f:
                    body = render(f.read(), tokens, rel)
                with open(dst, "w", encoding="utf-8") as f:
                    f.write(body)
            else:
                import shutil
                shutil.copy2(src, dst)
            count += 1

    modules = ["booth"]
    n_ch = n_mi = 0
    if has_show:
        show = json.loads(tokens["show_json"])
        n_ch, n_mi = len(show.get("chapters", [])), len(show.get("missions", []))
        modules += ["crew card", "handler console"]

    return {
        "out_dir": out_dir, "count": count, "skipped": sorted(set(skipped)),
        "brand_name": tokens["brand.name"], "brand_short": tokens["brand.short"],
        "primary": tokens["colors.primary"], "secondary": tokens["colors.secondary"],
        "logo_embedded": tokens["logo_data_uri"] != "null",
        "has_show": bool(has_show), "chapters": n_ch, "missions": n_mi, "modules": modules,
    }

def generate(config_path: str, out_dir: str) -> dict:
    with open(config_path, encoding="utf-8") as f:
        cfg = json.load(f)
    config_dir = os.path.dirname(os.path.abspath(config_path))
    r = generate_from_cfg(cfg, out_dir, config_dir)

    print(f"✓ Generated {r['brand_name']} → {out_dir}  ({r['count']} files)")
    print(f"  brand:   {r['brand_name']} ({r['brand_short']})")
    print(f"  colours: primary {r['primary']} · secondary {r['secondary']}")
    print(f"  logo:    {'embedded' if r['logo_embedded'] else 'text lockup (no logo file)'}")
    mods = "booth (index/gallery/setup + B2 + NAS)"
    if r["has_show"]:
        mods += f", crew card (player), handler console ({r['chapters']} chapters · {r['missions']} missions)"
    print(f"  modules: {mods}")
    if r["skipped"]:
        print(f"  skipped: {', '.join(r['skipped'])} (no \"show\" in config)")
    print()
    print("  Next: drag the folder onto app.netlify.com/drop, then follow SETUP.md.")
    return r

def main(argv=None):
    ap = argparse.ArgumentParser(description="Generate a branded photo-booth site from a JSON config.")
    ap.add_argument("config", help="path to a brand config JSON (see brands/gtad.json)")
    ap.add_argument("-o", "--out", help="output directory (default: build/<projectSlug>)")
    args = ap.parse_args(argv)

    with open(args.config, encoding="utf-8") as f:
        cfg = json.load(f)
    prefix = _get(cfg, "web", "storagePrefix", default="booth")
    slug = _get(cfg, "web", "projectSlug", default=f"{prefix}-photobooth")
    out = args.out or os.path.join("build", slug)
    generate(args.config, out)

if __name__ == "__main__":
    main()
