# Trackmania Oldest World Records Tracker

Static GitHub Pages site for tracking the longest-standing Trackmania 2020 world records on official seasonal campaign and Track of the Day maps.

## Local preview

```powershell
python -m http.server 8000 --directory site
```

Open `http://localhost:8000`.

## Fetch records locally

Create a local `.env` file with:

```env
UBI_EMAIL=...
UBI_PASS=...
TM_CLIENT_ID=...
TM_CLIENT_SECRET=...
```

For fewer Ubisoft login rate-limit problems, prefer a Trackmania dedicated server account for the Nadeo Live token:

```env
TM_DEDI_LOGIN=...
TM_DEDI_PASSWORD=...
TM_CLIENT_ID=...
TM_CLIENT_SECRET=...
```

Then run:

```powershell
python -m pip install -r requirements.txt
python scripts/fetch_records.py --out site/data --previous site/data/records.json
```

The script writes:

- `site/data/records.json`
- `site/data/recent_changes.json`
- `site/data/metadata.json`

## GitHub Pages

The `.github/workflows/deploy-pages.yml` workflow deploys `site/` to GitHub Pages.

Scheduled and manual workflow runs fetch fresh records first, commit updated JSON data, and deploy the refreshed static site. Pushes to `main` deploy the current `site/` contents.

Repository secrets required for scheduled fetching:

- `TM_CLIENT_ID`
- `TM_CLIENT_SECRET`

For Nadeo Live authentication, set either:

- `TM_DEDI_LOGIN` and `TM_DEDI_PASSWORD` preferred
- or `UBI_EMAIL` and `UBI_PASS` as fallback

Optional repository variable:

- `TM_USER_AGENT`, for a more specific API user agent string.
