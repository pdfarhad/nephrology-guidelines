# Renal guidelines reader

Encrypted static reference site (GitHub Pages). Page images are AES-256-GCM
encrypted at build time; the browser derives the key from the sign-in
credentials and decrypts client-side. Credentials are not stored in this repo.

Rebuild: `SITE_USER=... SITE_PASS=... python3 build.py` (requires the source
page images, which are not in this repo), then commit `static/` and push.
