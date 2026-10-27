
import asyncio
import json
from pathlib import Path
from urllib.parse import urljoin, urlparse

from playwright.async_api import async_playwright

BASE_URL = "http://127.0.0.1:8000/"
MAX_PAGES = 40

VIEWPORTS = [
    {"name": "mobile-320", "width": 320, "height": 740},
    {"name": "mobile-375", "width": 375, "height": 812},
    {"name": "mobile-430", "width": 430, "height": 932},
    {"name": "tablet-768", "width": 768, "height": 1024},
    {"name": "laptop-1024", "width": 1024, "height": 768},
    {"name": "laptop-1366", "width": 1366, "height": 768},
    {"name": "desktop-1920", "width": 1920, "height": 1080},
]

SKIP_PARTS = (
    "/admin/", "/logout/", "/delete/", "/remove/",
    "/checkout/", "/oauth/", "/accounts/"
)

OUTPUT = Path("responsive_report")
OUTPUT.mkdir(exist_ok=True)

def is_internal(url):
    parsed = urlparse(url)
    base = urlparse(BASE_URL)

    return (
        parsed.netloc == base.netloc
        and parsed.scheme in ("http", "https")
        and not any(part in parsed.path.lower() for part in SKIP_PARTS)
    )

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        discovered = [BASE_URL]
        visited = set()
        results = []

        # Discover internal pages by following links.
        while discovered and len(visited) < MAX_PAGES:
            url = discovered.pop(0)
            url = url.split("#")[0]

            if url in visited or not is_internal(url):
                continue

            visited.add(url)

            try:
                await page.goto(
                    url, wait_until="domcontentloaded", timeout=20000
                )
                await page.wait_for_timeout(500)

                links = await page.locator("a[href]").evaluate_all(
                    """els => els.map(a => a.href)"""
                )

                for link in links:
                    link = link.split("#")[0]
                    if is_internal(link) and link not in visited:
                        if link not in discovered:
                            discovered.append(link)

            except Exception as e:
                print(f"PAGE ERROR: {url} | {e}")

        print(f"\nFound {len(visited)} pages.\n")

        # Test every discovered page at every viewport.
        for url in sorted(visited):
            for viewport in VIEWPORTS:
                errors = []

                await page.set_viewport_size({
                    "width": viewport["width"],
                    "height": viewport["height"],
                })

                try:
                    response = await page.goto(
                        url, wait_until="domcontentloaded", timeout=20000
                    )
                    await page.wait_for_timeout(300)

                    if response and response.status >= 400:
                        errors.append(f"HTTP {response.status}")

                    dimensions = await page.evaluate("""() => ({
                        viewport: document.documentElement.clientWidth,
                        document: document.documentElement.scrollWidth,
                        body: document.body.scrollWidth,
                        title: document.title,
                        brokenImages: [...document.images]
                            .filter(i => i.complete && i.naturalWidth === 0)
                            .map(i => i.src),
                        overflowingElements: [...document.querySelectorAll('body *')]
                            .filter(el => {
                                const r = el.getBoundingClientRect();
                                const s = getComputedStyle(el);
                                return r.width > 0 &&
                                    (r.right > document.documentElement.clientWidth + 2 ||
                                     r.left < -2) &&
                                    s.position !== 'fixed' &&
                                    s.position !== 'absolute';
                            })
                            .slice(0, 10)
                            .map(el => ({
                                tag: el.tagName,
                                className: typeof el.className === 'string'
                                    ? el.className : '',
                                right: Math.round(el.getBoundingClientRect().right),
                                width: Math.round(el.getBoundingClientRect().width)
                            }))
                    })""")

                    if dimensions["document"] > dimensions["viewport"] + 2:
                        errors.append("HORIZONTAL OVERFLOW")

                    if dimensions["brokenImages"]:
                        errors.append("BROKEN IMAGES")

                    screenshot_name = (
                        f"{len(results):04d}_{viewport['name']}.png"
                    )
                    await page.screenshot(
                        path=str(OUTPUT / screenshot_name),
                        full_page=True
                    )

                    results.append({
                        "url": url,
                        "viewport": viewport,
                        "dimensions": dimensions,
                        "errors": errors,
                    })

                    status = " | ".join(errors) if errors else "OK"
                    print(
                        f"[{viewport['name']}] {url} -> {status}"
                    )

                except Exception as e:
                    results.append({
                        "url": url,
                        "viewport": viewport,
                        "errors": [str(e)],
                    })
                    print(f"FAILED: {url} | {e}")

        (OUTPUT / "report.json").write_text(
            json.dumps(results, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

        await browser.close()

        print("\nFinished!")
        print("Report: responsive_report/report.json")
        print("Screenshots: responsive_report/")

asyncio.run(main())
