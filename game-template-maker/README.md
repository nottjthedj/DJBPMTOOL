# Game Template Maker — Photo Booth

Recreate the **GTAD photo-booth** for any brand from a single config file.
Change the **colour scheme, web info, socials, and branding** in one JSON, run one
command, and get a complete, ready-to-deploy site — the same proven formula every time.

> The booth we sold: guests scan a QR at the event → open a branded camera on their
> phone → shoot a photo/video with your overlay burned in → save, share, and opt their
> shot into your gallery. You review/approve captures from a private gallery page.
> This tool stamps out that exact experience for a new brand in seconds.

---

## Quick start

```bash
# reproduce the original show
python3 make_booth.py brands/gtad.json

# spin up a brand-new one
cp brands/gtad.json brands/my-brand.json      # edit the values
python3 make_booth.py brands/my-brand.json     # -> build/<projectSlug>/
```

Output lands in `build/<projectSlug>/` — a full site (`index.html`, `gallery.html`,
`setup.html`, the Netlify functions, `netlify.toml`, `DEPLOY.md`, `SETUP.md`).
Drag that folder onto **app.netlify.com/drop**, then follow the generated `SETUP.md`.

No dependencies, no install — just Python 3.10+.

---

## What you change (and what stays)

**You change (per brand, in the config):**

| Group      | What it controls                                                            |
|------------|-----------------------------------------------------------------------------|
| `brand`    | Name, two-line logo lockup, short code, kicker, tagline, hashtag, CTA, logo |
| `colors`   | The whole colour scheme — background, primary, secondary, accent, text      |
| `socials`  | Instagram / Facebook / TikTok links + the @handle used in share captions    |
| `web`      | Domain, storage namespace, Netlify name, bucket name, CORS origins          |

**Stays the same (the formula):** the camera flow, the three photo frames
(Badge / Neon / Minimal), photo + 15-second video capture, the overlay renderer,
save/share/gallery upload, the operator gallery with approve/delete, QR event setup,
and the whole secure Backblaze-B2 upload pipeline.

---

## Config reference

Every field lives in `brands/*.json`. Required fields are marked ★; everything else
has a sensible default so a minimal config still produces a polished booth.

```jsonc
{
  "brand": {
    "name":        "Grand Theft After-Dark",   // ★ full name (titles, captions)
    "short":       "GTAD",                      // ★ short code (gallery, buttons)
    "lineOne":     "Grand Theft",               // ★ top line of the logo lockup
    "lineTwo":     "After-Dark",                // ★ bottom line of the logo lockup
    "kicker":      "★ Presents ★",              //   small label above the logo
    "tagline":     "Tap below to strike a pose.",
    "followLabel": "Follow the movement",       //   label above the social buttons
    "hashtag":     "#GrandTheftAfterDark",      //   default hashtag on every shot
    "galleryCta":  "Add to GTAD Gallery",       //   the opt-in button text
    "galleryDone": "Added to Gallery",          //   confirmation text
    "logo":        "gtad-logo.png"              //   white artwork on transparent/black;
                                                //   optional — omit for a text-only lockup
  },

  "colors": {                                   //   any valid #hex; omit any to keep the house value
    "bg":            "#0a0a0f",
    "primary":       "#ff1e6c",                 //   headline + primary buttons + glow
    "primaryBright": "#ff4f8b",
    "secondary":     "#16e0ff",                 //   secondary accent + approve/share
    "accent":        "#ffc23d",                 //   kicker / date highlights
    "ink":           "#f5f5fa",                 //   body text
    "dim":           "#9aa0b5"                  //   muted text
  },

  "socials": {
    "instagram": "https://instagram.com/grandtheftafterdark",
    "facebook":  "https://facebook.com/grandtheftafterdark",
    "tiktok":    "https://tiktok.com/@grandtheftafterdark",
    "igHandle":  "grandtheftafterdark"          //   used in the share caption; auto-derived if omitted
  },

  "web": {
    "storagePrefix": "gtad",                    // ★ namespace for this brand's saved settings + filenames
    "netlifyName":   "gtad",                     //   <name>.netlify.app  (default: storagePrefix)
    "primaryDomain": "booth.grandtheftafterdark.com",
    "rootDomain":    "grandtheftafterdark.com",
    "bucketName":    "gtad-booth-inbox",         //   Backblaze bucket (default: <prefix>-booth-inbox)
    "projectSlug":   "gtad-photobooth",          //   output folder name
    "corsRuleName":  "gtadBooth",
    "corsOrigins":   [                            //   origins allowed to upload/view (auto-built if omitted)
      "https://gtad.netlify.app",
      "https://booth.grandtheftafterdark.com",
      "https://grandtheftafterdark.com"
    ]
  }
}
```

### Colour scheme notes
- Only the seven base colours are set; the darker shadow/gradient shades used in the UI
  are **derived automatically** from them, so a new palette stays internally consistent.
- The colours flow everywhere — CSS, the neon glows, *and* the overlay burned into each
  photo/video — from these seven values.

### Logo notes
- Provide `brand.logo` as **white artwork on a transparent (or black) background**. The
  booth keys brightness → opacity and trims the margins, then embeds it (single file, no
  hosting needed) and burns it into every capture.
- Omit `brand.logo` and the booth falls back to a styled **text lockup** of
  `lineOne` / `lineTwo` (see the Midnight Arcade example).

---

## Files

```
game-template-maker/
├─ make_booth.py                  the generator (stdlib only)
├─ booth_config.schema.json       machine-readable config schema
├─ brands/
│  ├─ gtad.json                   the original show — reproduces GTAD-PHOTOBOOTH
│  ├─ gtad-logo.png               the GTAD logo (referenced by gtad.json)
│  └─ example-midnight-arcade.json  a second brand off the same formula
└─ templates/                     the tokenized master booth (source of truth)
   ├─ index.html  gallery.html  setup.html
   ├─ netlify.toml  DEPLOY.md  SETUP.md
   └─ netlify/functions/…         secure B2 upload + gallery API
```

To evolve the booth itself for **every** brand, edit `templates/`. To change **one**
brand, edit its `brands/*.json`. Regenerate and redeploy.

---

## Deploy (per brand, once)

1. `python3 make_booth.py brands/<brand>.json`
2. Drag `build/<projectSlug>/` onto **app.netlify.com/drop**.
3. Follow the generated **`SETUP.md`** — create the Backblaze bucket, add the five
   environment variables, point your domain. ~15 minutes.
4. Open `setup.html` on the site to generate the per-event QR code.

That's the whole loop. New brand = new config = new booth. Expand infinitely.
