import asyncio
import os

from patchright.async_api import async_playwright

COUPON_PAGE_URL = "https://hannaford.com/savings/coupons/browse"
# Persistent Chromium user-data dir so cookies/localStorage survive between runs
# and we can usually skip the fragile DataDome-gated login flow.
USER_DATA_DIR = "./.chrome-profile"
DEBUG_DIR = "./.debug-screenshots"

# JavaScript bookmarklet that clicks each available coupon clip button sequentially
# with a 1.5s delay between clicks to avoid rate limiting
CLIP_ALL_JS = """
javascript:(function() {  var buttons = Array.from(document.querySelectorAll('button[data-opens-modal="false"]'))    .filter(function(btn) {      return btn.textContent.trim().includes('Clip Coupon');    });    console.log('Found ' + buttons.length + ' coupons to clip');    function clipNext(index) {    if (index >= buttons.length) {      console.log('Done! All coupons clipped.');      return;    }    buttons[index].click();    console.log('Clipping ' + (index + 1) + '/' + buttons.length);    setTimeout(function() { clipNext(index + 1); }, 500);  }    clipNext(0);})();
"""


async def login(page, username: str, password: str) -> None:
    await page.goto("https://www.hannaford.com/")
    # Header has a "Sign In ⌄" dropdown trigger; clicking it reveals an inner
    # button whose text is exactly "Sign In" — that's the one that opens the form.
    sign_in_trigger = page.locator("text=Sign In").first
    await sign_in_trigger.wait_for(state="visible", timeout=60_000)
    await sign_in_trigger.click()
    inner_signin = page.get_by_role("button", name="Sign In", exact=True).last
    await inner_signin.wait_for(state="visible", timeout=10_000)
    await inner_signin.click()
    await page.locator('input[name="username"]').fill(username)
    await page.locator('input[name="password"]').fill(password)
    await page.get_by_role("button", name="Sign In").click()
    await page.wait_for_load_state("networkidle")


async def clip_coupons(page) -> None:
    await page.goto(COUPON_PAGE_URL)
    await page.wait_for_load_state("networkidle")

    async def click_show_more():
        try:
            await page.locator("#show-more").click(timeout=3000)
            await asyncio.sleep(5)
            await click_show_more()
        except Exception:
            pass

    await click_show_more()

    # Run the bookmarklet; it handles its own async timing via setTimeout
    await page.evaluate(CLIP_ALL_JS)
    # Poll until no "Clip Coupon" buttons remain rather than guessing a sleep time
    print("Waiting for all coupons to be clipped...")
    while True:
        remaining = await page.eval_on_selector_all(
            'button[data-opens-modal="false"]',
            "buttons => buttons.filter(b => b.textContent.trim().includes('Clip Coupon')).length",
        )
        if remaining == 0:
            break
        print(f"{remaining} coupons remaining...")
        await asyncio.sleep(2)
    print("Done clipping coupons.")


async def main() -> None:
    username = os.environ["HANNAFORD_USERNAME"]
    password = os.environ["HANNAFORD_PASSWORD"]
    # GitHub Actions runs headless; locally you can set HEADLESS=false to watch
    headless = os.environ.get("HEADLESS", "true").lower() != "false"

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            channel="chrome",
            headless=headless,
            viewport={"width": 1280, "height": 800},
        )
        page = context.pages[0] if context.pages else await context.new_page()
        try:
            # Use the coupon page itself as the auth probe: if we land there,
            # session is good; otherwise Hannaford redirects us to a sign-in URL.
            await page.goto(COUPON_PAGE_URL)
            await page.wait_for_load_state("networkidle")
            if "/savings/coupons/browse" in page.url:
                print("Reusing saved session.")
            else:
                print("No saved session — logging in to Hannaford...")
                await login(page, username, password)
                print("Login successful.")
            await clip_coupons(page)
        except Exception:
            await page.screenshot(path="failure.png", full_page=False)
            print("Screenshot saved to failure.png")
            raise
        finally:
            await context.close()


if __name__ == "__main__":
    asyncio.run(main())
