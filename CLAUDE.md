# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies (uses uv package manager)
uv sync

# Install Playwright browser (required after fresh uv sync)
uv run playwright install chromium --with-deps

# Run the scraper locally
HANNAFORD_USERNAME=you@example.com HANNAFORD_PASSWORD=secret uv run python clip_coupons.py

# Run with visible browser for debugging
HANNAFORD_USERNAME=you@example.com HANNAFORD_PASSWORD=secret HEADLESS=false uv run python clip_coupons.py
```

## Architecture

Single-file async Playwright script (`clip_coupons.py`) with three functions:

- `login(page, username, password)` — navigates to hannaford.com, fills the sign-in form, and waits for `networkidle`
- `clip_coupons(page)` — navigates to the coupon browse page, counts available tiles, then injects `CLIP_ALL_JS` (a jQuery bookmarklet) to click each clip button sequentially with 1.5s delays; blocks until all clicks should be done
- `main()` — reads credentials from `HANNAFORD_USERNAME`/`HANNAFORD_PASSWORD` env vars, launches Chromium (headless by default, controlled by `HEADLESS` env var), and calls the above two in order

The JS bookmarklet (`CLIP_ALL_JS`) uses jQuery already present on the site and recurses via `setTimeout` so Playwright only needs to `evaluate` it once, then sleep for `(count × 1.5s) + 3s`.

GitHub Actions runs this daily at 08:00 UTC via `.github/workflows/clip_coupons.yml`, using `HANNAFORD_USERNAME` and `HANNAFORD_PASSWORD` repository secrets.
