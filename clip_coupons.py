import os
import asyncio
from playwright.async_api import async_playwright

COUPON_PAGE_URL = "https://hannaford.com/savings/coupons/browse"

# JavaScript bookmarklet that clicks each available coupon clip button sequentially
# with a 1.5s delay between clicks to avoid rate limiting
CLIP_ALL_JS = """
(function($) {
    $.fn.pop = function() { var top = this.get(-1); this.splice(this.length-1,1); return top; };
    $.fn.shift = function() { var bottom = this.get(0); this.splice(0,1); return bottom; };
    clipper = function(coupons) {
        if (coupons.length === 0) return;
        coupons.pop().click();
        setTimeout(function() { clipper(coupons); }, 1500);
    };
    clipper($('.couponTile.available .clipTarget'));
})(jQuery);
"""


async def login(page, username: str, password: str) -> None:
    await page.goto("https://www.hannaford.com/")
    # Open sign-in modal/page
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

    async with async_playwright() as p:
        # GitHub Actions runs headless; locally you can set HEADLESS=false to watch
        headless = os.environ.get("HEADLESS", "true").lower() != "false"
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context()
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
