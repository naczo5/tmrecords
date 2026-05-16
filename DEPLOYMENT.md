# Deployment

This project is deployed as a static GitHub Pages site through GitHub Actions.

## Repository Settings

In GitHub, set Pages to deploy from **GitHub Actions**.

## Required Secrets

Add these repository secrets:

- `TM_CLIENT_ID`
- `TM_CLIENT_SECRET`

For Nadeo Live authentication, add either:

- `TM_DEDI_LOGIN` and `TM_DEDI_PASSWORD` preferred
- or `UBI_EMAIL` and `UBI_PASS` as fallback

## Workflow

`.github/workflows/deploy-pages.yml` runs on:

- pushes to `main`
- a 12-hour schedule
- manual `workflow_dispatch`

Scheduled and manual runs fetch data, commit changed JSON files under `site/data`, and deploy `site/`.

Push runs deploy the static site without fetching, so layout/content changes can publish without requiring API credentials.
