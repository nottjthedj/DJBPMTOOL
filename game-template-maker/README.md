# Game Template Maker — event platform edition

Recreate the **Grand Theft After-Dark** event system for any brand from a single set
of config files. Fill in the blanks, drop in your logo + show data, run one command,
and get a complete, deployable multi-module site — the same proven formula every time.

> **What GTAD is:** a live, lore-driven interactive game-show. Guests scan a QR on
> arrival, get "made" into the crew, and play through a night of missions run by the
> host ("the Handler"). This tool stamps out that whole experience — booth, crew card,
> and host console — re-skinned for a new brand.

---

## Modules it generates

| Module | File(s) | Who uses it | What it does |
|--------|---------|-------------|--------------|
| **Photo Booth** | `index.html`, `gallery.html`, `setup.html`, `netlify/` | guests + operator | Branded camera → photo/video with your overlay → save/share/opt-in. Includes the **gallery admin** (approve/delete) and the secure **Backblaze-B2 → NAS** pipeline. |
| **Crew Card** *(player)* | `crew.html` | guests | Scan-to-get-made card: member number, **tonight's Job** + Handler transmission, live **Wanted Level**, tonight's **missions**, and a link into the booth. |
| **Handler Console** *(admin)* | `handler.html` | the host | Chapter picker (your whole season), the opening-transmission **teleprompter**, a **mission picker** (pick 3, with props/how-to/VO), Wanted-Level control, and a **QR generator** that hands guests a crew card pre-loaded with tonight's setup. Links to the gallery. |

The Booth ships for every brand. The **Crew Card + Handler Console** are generated only
when the config includes a **`show`** (your chapters + missions) — see below.

---

## Quick start

```bash
# reproduce the real show (booth + crew card + handler console)
python3 make_booth.py brands/gtad.json

# a booth-only brand (no show data)
python3 make_booth.py brands/example-midnight-arcade.json
```

Output lands in `build/<projectSlug>/`. Drag that folder onto **app.netlify.com/drop**,
then follow the generated `SETUP.md`. No dependencies — just Python 3.10+.

---

## What you change (per brand)

| File | Controls |
|------|----------|
| `brands/<brand>.json` | Branding (name, logo lockup, kicker, hashtag, CTA, **legal line**), the **colour scheme**, socials, web/deploy info, and a pointer to the show file. |
| `brands/<brand>.show.json` | The **show**: your season of chapters (codename, act, the job, the Handler transmission) and your missions (props, how-it-runs, win, Handler VO, variation) + vocabulary and Wanted-Level labels. |
| your logo image | White-on-transparent PNG, embedded + burned into captures. Optional (text lockup fallback). |

Everything the formula keeps fixed — the camera flow, the three photo frames, the
crew-card mechanics, the console's teleprompter/mission-picker/QR tooling — stays put.

---

## Brand config reference (`brands/*.json`)

★ = required. Everything else has a sensible default.

```jsonc
{
  "brand": {
    "name": "Grand Theft After-Dark",   // ★ full name
    "short": "GTAD",                     // ★ short code
    "lineOne": "Grand Theft",            // ★ logo top line
    "lineTwo": "After-Dark",             // ★ logo bottom line
    "kicker": "★ Presents ★",
    "tagline": "Tap below to strike a pose.",
    "followLabel": "Follow the movement",
    "hashtag": "#GrandTheftAfterDark",
    "galleryCta": "Add to GTAD Gallery",
    "galleryDone": "Added to Gallery",
    "legal": "Independent fan tribute event. Not affiliated with …",  // footer disclaimer
    "logo": "gtad-logo.png"              // optional; text lockup if omitted
  },

  "show": "gtad.show.json",              // path (or inline object). Omit → booth-only.

  "colors": {                            // any #hex; darker shades are derived
    "bg": "#000000", "primary": "#FF1493", "primaryBright": "#ff4faf",
    "secondary": "#00E5E5", "accent": "#ffc23d", "ink": "#ffffff", "dim": "#8a8a94"
  },

  "socials": {
    "instagram": "https://instagram.com/grandtheftafterdark",
    "facebook":  "https://facebook.com/grandtheftafterdark",
    "tiktok":    "https://tiktok.com/@grandtheftafterdark",
    "igHandle":  "grandtheftafterdark"
  },

  "web": {
    "storagePrefix": "gtad",             // ★ namespace for saved settings/filenames
    "netlifyName": "gtad",
    "primaryDomain": "booth.grandtheftafterdark.com",
    "rootDomain": "grandtheftafterdark.com",
    "bucketName": "gtad-booth-inbox",
    "projectSlug": "gtad-photobooth",
    "corsRuleName": "gtadBooth",
    "corsOrigins": ["https://gtad.netlify.app", "https://booth.grandtheftafterdark.com"]
  }
}
```

## Show config reference (`brands/*.show.json`)

```jsonc
{
  "meta":     { "name": "…", "tagline": "…", "legal": "…" },
  "vocabulary": { "crew": "the attendees", "handler": "the host character", … },
  "wantedLevels": [ { "stars": 1, "label": "ON THE RADAR" }, … 5 ],
  "crewCard": { "madeHeadline": "YOU'RE MADE", "memberLabel": "MADE MEMBER", … },
  "chapters": [
    { "n": 1, "codename": "THE RECRUITMENT", "act": "Act I — Assembly the Crew",
      "job": "The crew gets made…", "endsOn": "…", "transmission": "Listen up…" }
    // …one per night of your season
  ],
  "missions": [
    { "n": 1, "name": "THE LINEUP", "category": "Stage Theatrical", "gtaRef": "Police lineup",
      "props": "…", "howItRuns": "…", "win": "…", "time": "3–4 min",
      "handlerVO": "Line 'em up…", "variation": "…" }
    // …your mission playbook
  ],
  "rotation": { "firstNight": [1,6,4], "returning": [10,7,9], "smallRoom": [8,11,5] }
}
```

`brands/gtad.show.json` is the real GTAD bible — **24 chapters** (a full 3-act season)
and **11 missions** — extracted from the production docs. Copy it to start a new show.

---

## Files

```
game-template-maker/
├─ make_booth.py               the generator (stdlib only)
├─ booth_config.schema.json    machine-readable brand-config schema
├─ brands/
│  ├─ gtad.json                the show — reproduces every module
│  ├─ gtad.show.json           24 chapters + 11 missions (the GTAD bible)
│  ├─ gtad-logo.png            the GTAD logo
│  └─ example-midnight-arcade.json   a booth-only rebrand (no show)
└─ templates/                  the tokenized masters (source of truth)
   ├─ index.html  gallery.html  setup.html      (booth)
   ├─ crew.html                                  (player: crew card)
   ├─ handler.html                               (admin: handler console)
   ├─ netlify.toml  DEPLOY.md  SETUP.md
   └─ netlify/functions/…                        (secure B2 upload + gallery API)
```

To evolve a module for **every** brand, edit `templates/`. To change **one** brand,
edit its `brands/*.json` (+ `*.show.json`). Regenerate and redeploy. New brand = new
config = the whole system, re-skinned. Expand infinitely.

---

## Notes

- **Colour scheme** flows everywhere — CSS, neon glows, the photo overlay, the crew
  card and console — from seven base colours; darker shades are derived automatically.
- **Live host→crowd sync is built in.** In the Handler Console, tap **Go Live** (enter
  your `GALLERY_TOKEN` once) and every crew phone follows the current chapter, Wanted
  Level and missions within a few seconds — change them on the Show/Missions tabs and
  the whole room updates. Guests scan **one static QR**; live state overrides whatever
  the QR encoded, and falls back to the QR's values when the show isn't live.
  - It reuses the booth's Backblaze B2 (state lives in `state/<event>.json`) via the
    `show-state` function — **no new service or config.** `GET /api/show-state?event=<key>`
    is public (phones poll it); `POST` requires the `GALLERY_TOKEN`.
  - **Per-event keys** — each room/city runs its own live channel. Set an **Event key**
    in the console (e.g. `chicago`, `detroit`); its crew QR carries `?e=<key>` and only
    that room follows it. Multiple shows run simultaneously without colliding. A bare
    `crew.html` (no `?e`) follows the default `main` channel, so single-room stays simple.
- The booth's own backend (Backblaze B2 + NAS) is unchanged and documented in the
  generated `SETUP.md`.
```
