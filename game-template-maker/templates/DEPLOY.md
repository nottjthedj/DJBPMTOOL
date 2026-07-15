# {{brand.short}} Booth — Auto-Deploy Setup (GitHub → Netlify)

The project folder is already a git repository with everything committed.
Do this once and future changes publish themselves.

## Step 1 — Put the code on GitHub (no terminal needed)
1. Download **GitHub Desktop** → https://desktop.github.com → install.
2. Open it and **sign in** (create a free GitHub account if you don't have one).
3. **File → Add local repository** → choose the folder:
   `/Users/nottjthedj/Music/{{web.projectSlug}}`
   (it's already initialized, so it'll recognize it).
4. Click **Publish repository** → keep **"Keep this code private" ✅ checked** → **Publish**.
   Your code is now on GitHub.

## Step 2 — Connect Netlify to the repo
1. Netlify → **Add new site → Import an existing project → Deploy with GitHub**.
2. **Authorize** GitHub → pick the **{{web.projectSlug}}** repo.
3. Build settings:
   - **Build command:** *(leave blank)*
   - **Publish directory:** `.`
   - (netlify.toml handles the functions automatically)
4. **Deploy site.**
5. This creates a NEW site, so on it:
   - Re-add the **5 environment variables** from SETUP.md (B2 keys + GALLERY_TOKEN).
   - **Domain settings** → re-point `{{web.primaryDomain}}` to this new site.

## After setup — how updates work
- When the booth is changed, the change is **committed + pushed** to GitHub, and Netlify
  **auto-rebuilds and publishes** within ~1 minute. No dragging, no manual deploys.
- To push a change yourself anytime: open **GitHub Desktop → Push origin**.

## Note
Because Git-connected Netlify sites are a fresh site (not the drag-drop one), the one-time
cost is: re-adding env vars + re-pointing the subdomain. After that it's fully hands-off.
