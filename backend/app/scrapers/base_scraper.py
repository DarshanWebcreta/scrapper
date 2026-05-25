import asyncio
import random
import logging
import httpx
from typing import Optional, Tuple
from app.config import settings

# If playwright is not installed, we can fall back to HTTPX
try:
    from playwright.async_api import async_playwright, Browser, Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logging.warning("Playwright is not installed. Scraping will use HTTPX fallback.")

logger = logging.getLogger("BaseScraper")

class BrowserManager:
    """Manages Playwright browser lifecycle and page fetching."""
    
    def __init__(self):
        self.pw = None
        self.browser = None
        self.use_playwright = PLAYWRIGHT_AVAILABLE

    async def start(self):
        """Initialize Playwright browser."""
        if self.use_playwright and not self.browser:
            try:
                self.pw = await async_playwright().start()
                # Run headless, with arguments to reduce bot-detection / blockings
                self.browser = await self.pw.chromium.launch(
                    headless=True,
                    args=[
                        "--disable-gpu",
                        "--disable-dev-shm-usage",
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-infobars",
                        "--window-position=0,0",
                        "--ignore-certificate-errors",
                        "--ignore-certificate-errors-spki-list"
                    ]
                )
                logger.info("Playwright Chromium browser started successfully.")
            except Exception as e:
                logger.error(f"Failed to start Playwright browser: {e}. Falling back to HTTPX.")
                self.use_playwright = False

    async def close(self):
        """Close browser instance."""
        if self.browser:
            try:
                await self.browser.close()
            except Exception:
                pass
            self.browser = None
        if self.pw:
            try:
                await self.pw.stop()
            except Exception:
                pass
            self.pw = None
        logger.info("Playwright browser closed.")

    def get_random_user_agent(self) -> str:
        """Pick a random User-Agent from the configured list."""
        if settings.USER_AGENT_ROTATION and settings.USER_AGENTS:
            return random.choice(settings.USER_AGENTS)
        return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    async def fetch_page_content_httpx(self, url: str) -> Tuple[str, int]:
        """Fallback fetching using HTTPX."""
        headers = {
            "User-Agent": self.get_random_user_agent(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Referer": "https://www.google.com/",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        }
        try:
            async with httpx.AsyncClient(headers=headers, timeout=settings.CRAWL_TIMEOUT, follow_redirects=True) as client:
                response = await client.get(url)
                return response.text, response.status_code
        except Exception as e:
            logger.debug(f"HTTPX request failed for {url}: {e}")
            return "", 500

    async def fetch_page_content(self, url: str) -> Tuple[str, int]:
        """
        Fetch HTML content from a URL.
        Uses Playwright if available, otherwise falls back to HTTPX.
        """
        if not self.use_playwright:
            return await self.fetch_page_content_httpx(url)
            
        # Ensure browser is started
        if not self.browser:
            await self.start()
            if not self.browser:
                # Started failed, fallback
                return await self.fetch_page_content_httpx(url)

        context = None
        page = None
        try:
            user_agent = self.get_random_user_agent()
            context = await self.browser.new_context(
                user_agent=user_agent,
                viewport={"width": 1280, "height": 800},
                ignore_https_errors=True
            )
            
            page = await context.new_page()
            # Set default timeout
            page.set_default_timeout(settings.CRAWL_TIMEOUT * 1000)
            
            # Navigate
            response = await page.goto(url, wait_until="domcontentloaded")
            status = response.status if response else 200
            
            # Wait a short random time to simulate human behavior
            await asyncio.sleep(random.uniform(0.5, 1.5))
            
            content = await page.content()
            return content, status
            
        except Exception as e:
            logger.debug(f"Playwright navigation failed for {url}: {e}. Retrying with HTTPX fallback...")
            # Fallback immediately to HTTPX if playwright fails (e.g. timeout or web-sockets block)
            return await self.fetch_page_content_httpx(url)
        finally:
            if page:
                try:
                    await page.close()
                except Exception:
                    pass
            if context:
                try:
                    await context.close()
                except Exception:
                    pass

# Singleton browser manager for reuse during scraping run
browser_manager = BrowserManager()
