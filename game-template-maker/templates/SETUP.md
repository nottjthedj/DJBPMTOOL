# {{brand.short}} Photo Booth — Setup Checklist

Do these once. ~15–20 minutes. Order matters: Backblaze → Netlify → Synology → Test.

---

## PART 1 — Backblaze B2 (your cloud "inbox")

1. Go to **backblaze.com** → create a free account → sign in.
2. Left menu **B2 Cloud Storage → Buckets → Create a Bucket**:
   - **Bucket Unique Name:** `{{web.bucketName}}` (if taken, add a suffix like `-{{web.storagePrefix}}`)
   - **Files in Bucket are:** **Private**
   - **Object Lock:** Disable
   - Click **Create a Bucket**.
3. On the bucket, note the **Endpoint** — e.g. `s3.us-west-004.backblazeb2.com`.
   - Your **region** is the middle chunk: `us-west-004`. Write it down.
4. Left menu **Application Keys → Add a New Application Key**:
   - **Name:** `{{web.storagePrefix}}-booth`
   - **Allow access to Bucket(s):** select **{{web.bucketName}}** (restrict to just it)
   - **Type of Access:** **Read and Write**
   - Click **Create New Key**.
   - ⚠️ **Copy `keyID` and `applicationKey` NOW** — the applicationKey is shown only once.

You now have: **keyID**, **applicationKey**, **bucket name**, **region**.

---

## PART 2 — Deploy the booth + add the keys (Netlify)

1. Deploy the **whole `{{web.projectSlug}}` folder** (not just index.html):
   - New site: drag the folder onto **app.netlify.com/drop**.
   - Existing site: open it → **Deploys** → drag the folder onto the deploy area.
   - Netlify auto-detects `netlify.toml` and the functions.
2. Site → **Site configuration → Environment variables → Add a variable** — add these five:

   | Key | Value |
   |-----|-------|
   | `B2_KEY_ID`     | your keyID |
   | `B2_APP_KEY`    | your applicationKey |
   | `B2_BUCKET`     | `{{web.bucketName}}` |
   | `B2_REGION`     | `us-west-004` (your region) |
   | `GALLERY_TOKEN` | a passcode you invent (unlocks the gallery) |

3. **Deploys → Trigger deploy → Deploy site** (env vars only apply to the *next* deploy).

---

## PART 3 — Synology Cloud Sync (bucket → your NAS)

1. **DSM → Package Center** → search **Cloud Sync** → **Install** → **Open**.
2. Click **+** → choose **Backblaze B2** → sign in with:
   - **Key ID / Account ID:** your keyID
   - **Application Key:** your applicationKey
3. Configure the task:
   - **Bucket:** `{{web.bucketName}}`
   - **Remote path:** `/` (root — pulls both `incoming/` and `approved/`)
   - **Local path:** a NAS folder, e.g. `/photobooth`
   - **Sync direction:** **Download remote changes only** (one-way, B2 → NAS)
   - **Advanced → enable** "Don't remove files in the destination folder when removed in source" (so your NAS keeps everything even if B2 is cleaned up)
4. **Apply / Done.** It syncs now and then watches continuously.

### Optional — keep B2 in the free tier
Once you've confirmed sync works, Backblaze bucket → **Lifecycle Settings** → delete files after e.g. **7 days**. B2 becomes a transient relay; your NAS keeps the originals.
*(Only do this after sync is proven, or you could delete before the NAS copies.)*

---

## PART 4 — Test the whole chain

1. Open the booth on your phone → take a **photo** with **"Add to {{brand.short}}'s gallery" checked** → tap **Save**.
   - You should see the toast **"Added to {{brand.short}} gallery ✓"**.
2. **Backblaze → Browse Files → {{web.bucketName}} → incoming/** → your file is there.
3. Open **{{web.primaryDomain}}/gallery.html** → enter your `GALLERY_TOKEN` → the shot shows under **New**. Tap **✓ Approve**.
4. Within ~1 minute, check the NAS `/photobooth/incoming/...` (and `/photobooth/approved/...`) → files synced.

---

## Troubleshooting

- **Gallery/upload says "Uploader not configured"** → an env var is missing, or you didn't redeploy after adding them.
- **Gallery says wrong passcode** → `GALLERY_TOKEN` value must match exactly what you type.
- **Upload toast never appears / gallery empty** → confirm `B2_REGION` exactly matches the bucket's endpoint, and the app key has **Read and Write** on the bucket.
- **Signature errors** → almost always a region mismatch. Fix `B2_REGION`, redeploy.
- **Cloud Sync won't connect** → re-check keyID/applicationKey; make sure the app key isn't over-restricted.

---

## Reference — where everything lives

- **Guests:** `{{web.primaryDomain}}` — shoot, save, share, opt-in
- **You:** `{{web.primaryDomain}}/gallery.html` — review, approve, delete
- **Raw uploads:** B2 `incoming/` → NAS `/photobooth/incoming/`
- **Approved set:** B2 `approved/` → NAS `/photobooth/approved/`
