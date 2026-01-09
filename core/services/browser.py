"""
Playwright-based browser helper for scraping sites that block simple HTTP clients.

Notes:
- Uses Chromium headless by default.
- Keeps implementation minimal and robust for Amazon/Flipkart search pages.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class BrowserFetchResult:
    url: str
    html: str
    status: Optional[int] = None


def fetch_rendered_html(url: str, *, wait_until: str = "domcontentloaded", timeout_ms: int = 30000) -> Optional[BrowserFetchResult]:
    """
    Fetch a page using Playwright Chromium and return rendered HTML.

    Returns None if Playwright isn't available or fetch fails.
    """
    try:
        from playwright.sync_api import sync_playwright
        from playwright_stealth import Stealth
    except Exception as e:
        print(f"Playwright/Stealth not available: {e}")
        return None

    try:
        with sync_playwright() as p:
            # Revert to Chromium for stealth
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                ],
            )
            context = browser.new_context(
                # Stealth plugin handles User-Agent and others, but good to set viewport/locale
                viewport={"width": 1280, "height": 720},
                locale="en-US",
            )
            page = context.new_page()
            
            # Apply stealth
            Stealth().apply_stealth_sync(page)
            
            resp = page.goto(url, wait_until=wait_until, timeout=timeout_ms)

            # Some sites show cookie banners/popups; attempt common dismiss patterns (best-effort)
            try:
                for selector in [
                    "button#sp-cc-accept",
                    "input#sp-cc-accept",
                    "button:has-text(\"Accept\")",
                    "button:has-text(\"I agree\")",
                    "button:has-text(\"Continue\")",
                ]:
                    el = page.query_selector(selector)
                    if el:
                        el.click(timeout=1000)
                        break
            except Exception:
                pass

            # Give scripts a moment to render key content
            try:
                page.wait_for_timeout(1200)
            except Exception:
                pass

            html = page.content()
            final_url = page.url
            status = None
            try:
                status = resp.status if resp else None
            except Exception:
                status = None

            context.close()
            browser.close()

            if not html or len(html) < 1000:
                return None
            return BrowserFetchResult(url=final_url, html=html, status=status)
    except Exception as e:
        print(f"Playwright fetch failed for {url}: {e}")
        return None

