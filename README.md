# Hannaford Coupon Scraper

Automates signing in to hannaford.com and clipping available digital coupons.

## One-time setup

```bash
uv sync
uv run playwright install chromium --with-deps
```

Create a `.env` file in this folder:

```bash
HANNAFORD_USERNAME=you@example.com
HANNAFORD_PASSWORD=your_password
HEADLESS=true
```

## Run manually

```bash
uv run --env-file .env python clip_coupons.py
```

## Run daily with cron (macOS)

1. Open crontab:

```bash
crontab -e
```

2. Add this line to run every day at 8:00 AM local time:

```cron
0 8 * * * /bin/zsh -lc 'cd /Users/ddelarosa/Dev/Personal/hannaford-coupon-scraper && source .venv/bin/activate && uv run --env-file .env python clip_coupons.py >> cron.log 2>&1'
```

3. Verify:

```bash
crontab -l
```

Notes:
- `cron.log` is written in the project directory.
- Update the minute/hour in the cron expression to choose a different time.
