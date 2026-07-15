#!/usr/bin/env python3
"""
Booth Studio — desktop app for the Game Template Maker.

Fill in a brand, drop in a logo, click Generate. Out comes a complete, ready-to-
deploy event site (photo booth + crew card + handler console), no terminal needed.
Package it into a double-click app with PyInstaller (see build-booth-studio.yml).

Runs on the standard library only (Tkinter ships with Python on Windows/macOS).
"""
import json, os, sys, subprocess, traceback
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser

import make_booth as mb  # reuse the exact generator (single source of truth)

# ---- palette (loose nod to the house style; Tk theming is limited) ----
BG, CARD, INK, DIM, PINK, TEAL = "#12121a", "#1b1b26", "#f5f5fa", "#9aa0b5", "#ff2d80", "#16e0ff"

COLOR_FIELDS = [
    ("bg", "Background"), ("primary", "Primary"), ("primaryBright", "Primary (bright)"),
    ("secondary", "Secondary"), ("accent", "Accent"), ("ink", "Text"), ("dim", "Muted text"),
]
BRAND_FIELDS = [
    ("name", "Brand name *", "Grand Theft After-Dark"),
    ("short", "Short code *", "GTAD"),
    ("lineOne", "Logo line 1 *", "Grand Theft"),
    ("lineTwo", "Logo line 2 *", "After-Dark"),
    ("kicker", "Kicker", "★ Presents ★"),
    ("tagline", "Tagline", "Tap below to strike a pose."),
    ("hashtag", "Hashtag", "#GrandTheftAfterDark"),
    ("legal", "Legal / disclaimer line", ""),
]
SOCIAL_FIELDS = [
    ("instagram", "Instagram URL"), ("facebook", "Facebook URL"),
    ("tiktok", "TikTok URL"), ("igHandle", "IG @handle (share caption)"),
]
WEB_FIELDS = [
    ("storagePrefix", "Storage prefix * (lowercase)", "gtad"),
    ("primaryDomain", "Primary domain", "booth.grandtheftafterdark.com"),
    ("rootDomain", "Root domain", "grandtheftafterdark.com"),
    ("netlifyName", "Netlify site name", "gtad"),
    ("projectSlug", "Output folder name", "gtad-photobooth"),
]


class BoothStudio(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Booth Studio — Game Template Maker")
        self.geometry("760x820")
        self.configure(bg=BG)
        self.vars = {}          # field key -> StringVar
        self.swatches = {}      # color key -> label widget
        self.logo_path = tk.StringVar(value="")
        self.show_mode = tk.StringVar(value="gtad")
        self.show_path = tk.StringVar(value="")
        self._build_style()
        self._build_ui()
        self._load_preset()      # start demo-ready with the GTAD preset

    # ---------------------------------------------------------------- styling
    def _build_style(self):
        s = ttk.Style(self)
        try: s.theme_use("clam")
        except Exception: pass
        s.configure(".", background=BG, foreground=INK, fieldbackground=CARD,
                    bordercolor="#33333f", lightcolor=CARD, darkcolor=CARD)
        s.configure("TFrame", background=BG)
        s.configure("Card.TFrame", background=CARD)
        s.configure("TLabel", background=BG, foreground=INK)
        s.configure("Dim.TLabel", background=BG, foreground=DIM, font=("TkDefaultFont", 9))
        s.configure("H.TLabel", background=BG, foreground=PINK,
                    font=("TkDefaultFont", 11, "bold"))
        s.configure("TEntry", fieldbackground=CARD, foreground=INK, insertcolor=INK)
        s.configure("TButton", background="#2a2a38", foreground=INK, padding=6)
        s.map("TButton", background=[("active", "#3a3a4c")])
        s.configure("Go.TButton", background=PINK, foreground="#ffffff",
                    font=("TkDefaultFont", 11, "bold"), padding=10)
        s.map("Go.TButton", background=[("active", "#ff4f96")])
        s.configure("TRadiobutton", background=BG, foreground=INK)
        s.map("TRadiobutton", background=[("active", BG)])

    # ---------------------------------------------------------------- layout
    def _build_ui(self):
        # top bar
        top = ttk.Frame(self); top.pack(fill="x", padx=14, pady=(12, 6))
        ttk.Label(top, text="BOOTH STUDIO", style="H.TLabel",
                  font=("TkDefaultFont", 15, "bold")).pack(side="left")
        ttk.Button(top, text="Load GTAD preset", command=self._load_preset).pack(side="right")
        ttk.Button(top, text="Open config…", command=self._open_config).pack(side="right", padx=6)
        ttk.Button(top, text="Save config…", command=self._save_config).pack(side="right")
        ttk.Label(self, text="Fill the blanks, pick your colours and logo, then Generate a "
                  "ready-to-deploy site.", style="Dim.TLabel").pack(anchor="w", padx=16)

        # scrollable body
        wrap = ttk.Frame(self); wrap.pack(fill="both", expand=True, padx=8, pady=8)
        canvas = tk.Canvas(wrap, bg=BG, highlightthickness=0)
        sb = ttk.Scrollbar(wrap, orient="vertical", command=canvas.yview)
        body = ttk.Frame(canvas)
        body.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=body, anchor="nw", width=720)
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side="left", fill="both", expand=True); sb.pack(side="right", fill="y")
        self.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-e.delta / 120), "units"))
        self.bind_all("<Button-4>", lambda e: canvas.yview_scroll(-1, "units"))
        self.bind_all("<Button-5>", lambda e: canvas.yview_scroll(1, "units"))

        self._section(body, "Brand")
        for key, label, _ph in BRAND_FIELDS:
            self._text_row(body, key, label)

        self._section(body, "Colour scheme")
        for key, label in COLOR_FIELDS:
            self._color_row(body, key, label)

        self._section(body, "Logo")
        row = ttk.Frame(body); row.pack(fill="x", pady=3)
        ttk.Label(row, text="Logo image (PNG, white-on-transparent — optional)",
                  width=34).pack(side="left")
        ttk.Entry(row, textvariable=self.logo_path).pack(side="left", fill="x", expand=True, padx=6)
        ttk.Button(row, text="Browse…", command=self._pick_logo).pack(side="left")
        ttk.Button(row, text="Clear", command=lambda: self.logo_path.set("")).pack(side="left", padx=4)

        self._section(body, "Show (crew card + handler console)")
        for val, label in [("gtad", "Use the Grand Theft After-Dark show (24 chapters, 11 missions)"),
                           ("none", "Booth only — no crew card / handler"),
                           ("custom", "Custom show file…")]:
            ttk.Radiobutton(body, text=label, value=val, variable=self.show_mode,
                            command=self._toggle_show).pack(anchor="w")
        self.show_row = ttk.Frame(body)
        ttk.Entry(self.show_row, textvariable=self.show_path).pack(side="left", fill="x", expand=True)
        ttk.Button(self.show_row, text="Browse…", command=self._pick_show).pack(side="left", padx=6)

        self._section(body, "Socials")
        for key, label in SOCIAL_FIELDS:
            self._text_row(body, key, label)

        self._section(body, "Web / deploy")
        for key, label, _ph in WEB_FIELDS:
            self._text_row(body, key, label)

        # footer / generate
        foot = ttk.Frame(self); foot.pack(fill="x", padx=14, pady=10)
        self.status = ttk.Label(foot, text="", style="Dim.TLabel"); self.status.pack(side="left")
        ttk.Button(foot, text="Generate site…", style="Go.TButton",
                   command=self._generate).pack(side="right")

    def _section(self, parent, title):
        ttk.Label(parent, text=title.upper(), style="H.TLabel").pack(anchor="w", pady=(14, 4))
        ttk.Separator(parent).pack(fill="x", pady=(0, 6))

    def _text_row(self, parent, key, label):
        row = ttk.Frame(parent); row.pack(fill="x", pady=3)
        ttk.Label(row, text=label, width=34).pack(side="left")
        v = tk.StringVar(); self.vars[key] = v
        ttk.Entry(row, textvariable=v).pack(side="left", fill="x", expand=True)

    def _color_row(self, parent, key, label):
        row = ttk.Frame(parent); row.pack(fill="x", pady=3)
        ttk.Label(row, text=label, width=34).pack(side="left")
        v = tk.StringVar(); self.vars[key] = v
        e = ttk.Entry(row, textvariable=v, width=12); e.pack(side="left")
        sw = tk.Label(row, width=4, bg=CARD, relief="solid", bd=1); sw.pack(side="left", padx=6)
        self.swatches[key] = sw
        v.trace_add("write", lambda *a, k=key: self._paint_swatch(k))
        ttk.Button(row, text="Pick…", command=lambda k=key: self._pick_color(k)).pack(side="left")

    # ---------------------------------------------------------------- helpers
    def _paint_swatch(self, key):
        val = self.vars[key].get().strip()
        try:
            self.swatches[key].configure(bg=val if val else CARD)
        except tk.TclError:
            self.swatches[key].configure(bg=CARD)

    def _pick_color(self, key):
        cur = self.vars[key].get().strip() or "#000000"
        try:
            rgb, hx = colorchooser.askcolor(color=cur, parent=self)
        except tk.TclError:
            rgb, hx = colorchooser.askcolor(parent=self)
        if hx:
            self.vars[key].set(hx)

    def _pick_logo(self):
        p = filedialog.askopenfilename(title="Choose a logo PNG",
                                       filetypes=[("Images", "*.png *.jpg *.jpeg"), ("All", "*.*")])
        if p:
            self.logo_path.set(p)

    def _pick_show(self):
        p = filedialog.askopenfilename(title="Choose a show JSON",
                                       filetypes=[("JSON", "*.json"), ("All", "*.*")])
        if p:
            self.show_path.set(p); self.show_mode.set("custom"); self._toggle_show()

    def _toggle_show(self):
        if self.show_mode.get() == "custom":
            self.show_row.pack(fill="x", pady=3)
        else:
            self.show_row.pack_forget()

    # ---------------------------------------------------------------- presets / io
    def _load_preset(self):
        path = os.path.join(mb.BRANDS, "gtad.json")
        try:
            with open(path, encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception as e:
            self.status.configure(text=f"(preset unavailable: {e})"); return
        self._apply_cfg(cfg, base_dir=mb.BRANDS)
        # bundled logo + show
        logo = os.path.join(mb.BRANDS, "gtad-logo.png")
        self.logo_path.set(logo if os.path.exists(logo) else "")
        self.show_mode.set("gtad"); self.show_path.set(""); self._toggle_show()
        self.status.configure(text="Loaded the Grand Theft After-Dark preset.")

    def _apply_cfg(self, cfg, base_dir="."):
        brand, colors = cfg.get("brand", {}), cfg.get("colors", {})
        soc, web = cfg.get("socials", {}), cfg.get("web", {})
        for k, _l, _p in BRAND_FIELDS:
            self.vars[k].set(brand.get(k, ""))
        for k, _l in COLOR_FIELDS:
            self.vars[k].set(colors.get(k, ""))
        for k, _l in SOCIAL_FIELDS:
            self.vars[k].set(soc.get(k, ""))
        for k, _l, _p in WEB_FIELDS:
            self.vars[k].set(web.get(k, ""))
        lg = brand.get("logo")
        if lg:
            self.logo_path.set(lg if os.path.isabs(lg) else os.path.join(base_dir, lg))
        show = cfg.get("show")
        if isinstance(show, str):
            sp = show if os.path.isabs(show) else os.path.join(base_dir, show)
            self.show_mode.set("custom"); self.show_path.set(sp)
        elif show:
            self.show_mode.set("custom")
        else:
            self.show_mode.set("none")
        self._toggle_show()

    def _collect_cfg(self):
        def grp(fields):
            return {k: self.vars[k].get().strip() for k, *_ in fields if self.vars[k].get().strip()}
        cfg = {
            "brand": grp(BRAND_FIELDS),
            "colors": grp(COLOR_FIELDS),
            "socials": grp(SOCIAL_FIELDS),
            "web": grp(WEB_FIELDS),
        }
        if self.logo_path.get().strip():
            cfg["brand"]["logo"] = self.logo_path.get().strip()
        mode = self.show_mode.get()
        if mode == "gtad":
            cfg["show"] = os.path.join(mb.BRANDS, "gtad.show.json")
        elif mode == "custom" and self.show_path.get().strip():
            cfg["show"] = self.show_path.get().strip()
        return cfg

    def _save_config(self):
        p = filedialog.asksaveasfilename(defaultextension=".json",
                                         filetypes=[("JSON", "*.json")], initialfile="brand.json")
        if not p:
            return
        cfg = self._collect_cfg()
        # store logo/show as they are; a shared config keeps absolute paths
        with open(p, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        self.status.configure(text=f"Saved config → {os.path.basename(p)}")

    def _open_config(self):
        p = filedialog.askopenfilename(filetypes=[("JSON", "*.json"), ("All", "*.*")])
        if not p:
            return
        try:
            with open(p, encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception as e:
            messagebox.showerror("Couldn't open", str(e)); return
        self._apply_cfg(cfg, base_dir=os.path.dirname(os.path.abspath(p)))
        self.status.configure(text=f"Loaded {os.path.basename(p)}")

    # ---------------------------------------------------------------- generate
    def _generate(self):
        cfg = self._collect_cfg()
        missing = [lbl for grp, flds in [("brand", BRAND_FIELDS[:4]), ("web", WEB_FIELDS[:1])]
                   for k, lbl, *_ in flds if not cfg.get(grp, {}).get(k)]
        if missing:
            messagebox.showwarning("Missing required fields",
                                   "Please fill:\n• " + "\n• ".join(missing)); return
        out_root = filedialog.askdirectory(title="Where should the site folder go?")
        if not out_root:
            return
        slug = cfg.get("web", {}).get("projectSlug") or (cfg["web"]["storagePrefix"] + "-photobooth")
        out_dir = os.path.join(out_root, slug)
        try:
            r = mb.generate_from_cfg(cfg, out_dir, config_dir=".")
        except SystemExit as e:
            messagebox.showerror("Couldn't generate", str(e)); return
        except Exception:
            messagebox.showerror("Couldn't generate", traceback.format_exc()); return
        mods = ", ".join(r["modules"])
        extra = f"\n{r['chapters']} chapters · {r['missions']} missions" if r["has_show"] else ""
        self.status.configure(text=f"Generated {r['brand_name']} → {out_dir}")
        if messagebox.askyesno("Site generated ✓",
                               f"{r['brand_name']} — {r['count']} files\nModules: {mods}{extra}\n\n"
                               f"Saved to:\n{out_dir}\n\nOpen the folder now?"):
            self._open_folder(out_dir)

    def _open_folder(self, path):
        try:
            if sys.platform.startswith("win"):
                os.startfile(path)  # noqa
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception:
            pass


def _selftest(out_dir):
    """Freeze smoke test: generate the GTAD preset from bundled resources, no GUI.
    Triggered by BOOTH_STUDIO_SELFTEST=<dir>. Proves a packaged build finds its
    templates/brands and produces a site."""
    with open(os.path.join(mb.BRANDS, "gtad.json"), encoding="utf-8") as f:
        cfg = json.load(f)
    r = mb.generate_from_cfg(cfg, out_dir, config_dir=mb.BRANDS)
    with open(os.path.join(out_dir, "_selftest.json"), "w", encoding="utf-8") as f:
        json.dump(r, f)
    print("SELFTEST OK", r["count"], "files;", r["modules"])


def main():
    st = os.environ.get("BOOTH_STUDIO_SELFTEST")
    if st:
        _selftest(st); return
    BoothStudio().mainloop()


if __name__ == "__main__":
    main()
