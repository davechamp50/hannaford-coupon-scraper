import os
import asyncio
from patchright.async_api import async_playwright

COUPON_PAGE_URL = "https://hannaford.com/savings/coupons/browse"

# JavaScript bookmarklet that clicks each available coupon clip button sequentially
# with a 1.5s delay between clicks to avoid rate limiting
CLIP_ALL_JS = """
javascript:(function() {  var buttons = Array.from(document.querySelectorAll('button[data-opens-modal="false"]'))    .filter(function(btn) {      return btn.textContent.trim().includes('Clip Coupon');    });    console.log('Found ' + buttons.length + ' coupons to clip');    function clipNext(index) {    if (index >= buttons.length) {      console.log('Done! All coupons clipped.');      return;    }    buttons[index].click();    console.log('Clipping ' + (index + 1) + '/' + buttons.length);    setTimeout(function() { clipNext(index + 1); }, 1500);  }    clipNext(0);})();
"""


async def login(page, username: str, password: str) -> None:
    await page.goto("https://www.hannaford.com/")
    # Wait up to 60s for DataDome's JS verification to complete and reveal the real page
    await page.get_by_role("link", name="Sign In").first.wait_for(timeout=60_000)
    await page.get_by_role("link", name="Sign In").first.click()
    await page.get_by_label("Email").fill(username)
    await page.get_by_label("Password").fill(password)
    await page.get_by_role("button", name="Sign In").click()
    # Wait for navigation to confirm login succeeded
    await page.wait_for_load_state("networkidle")


async def clip_coupons(page) -> None:
    await page.goto(COUPON_PAGE_URL)
    await page.wait_for_load_state("networkidle")
    # Count available coupons before clipping for logging
    available = await page.locator(".couponTile.available .clipTarget").count()
    print(f"Found {available} unclipped coupon(s)")
    if available == 0:
        print("Nothing to clip.")
        return
    # Run the bookmarklet; it handles its own async timing via setTimeout
    await page.evaluate(CLIP_ALL_JS)
    # Wait long enough for all sequential clicks to finish (1.5s * count + buffer)
    wait_ms = available * 1500 + 3000
    print(f"Waiting {wait_ms / 1000:.1f}s for all coupons to be clipped...")
    await asyncio.sleep(wait_ms / 1000)
    print("Done clipping coupons.")


async def main() -> None:
    username = os.environ["HANNAFORD_USERNAME"]
    password = os.environ["HANNAFORD_PASSWORD"]
    # GitHub Actions runs headless; locally you can set HEADLESS=false to watch
    headless = os.environ.get("HEADLESS", "true").lower() != "false"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
        )
        page = await context.new_page()
        try:
            print("Logging in to Hannaford...")
            await login(page, username, password)
            print("Login successful. Navigating to coupons...")
            await clip_coupons(page)
        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
