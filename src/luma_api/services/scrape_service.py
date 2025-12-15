"""Service for scraping and converting HTML to markdown using Claude."""

import logging

import httpx
from playwright.async_api import async_playwright

from luma_api.config import get_settings

logger = logging.getLogger(__name__)

MARKDOWN_CONVERSION_PROMPT = """Below is raw html data for a website, convert it to proper \
markdown format. Remove all ads, header and footer can be added into appendix at the end.

Return ONLY the markdown content, no explanations or wrapper text.

HTML Content:
"""


class ScrapeService:
    """Service for scraping URLs and converting HTML to markdown using Claude."""

    def __init__(self) -> None:
        self.settings = get_settings()

    async def scrape_url(self, url: str) -> str:
        """
        Scrape a URL using Playwright headless browser.

        If PLAYWRIGHT_WS_ENDPOINT is configured, connects to a remote Playwright server.
        Otherwise falls back to local Playwright.

        Args:
            url: URL to scrape

        Returns:
            HTML content of the page
        """
        async with async_playwright() as p:
            # Connect to remote Playwright server if endpoint is configured
            ws_endpoint = self.settings.playwright_ws_endpoint
            if ws_endpoint:
                logger.info("Connecting to remote Playwright at %s", ws_endpoint)
                browser = await p.chromium.connect(ws_endpoint)
            else:
                logger.info("Using local Playwright browser")
                browser = await p.chromium.launch(headless=True)

            user_agent = (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent=user_agent,
            )
            page = await context.new_page()

            try:
                # Navigate to URL with timeout
                await page.goto(url, wait_until="networkidle", timeout=30000)

                # Wait a bit for dynamic content
                await page.wait_for_timeout(2000)

                # Get the HTML content
                html = await page.content()

                return html

            finally:
                await context.close()
                await browser.close()

    async def convert_html_to_markdown(self, html_content: str) -> str:
        """
        Convert HTML content to markdown using Claude Sonnet 4.5.

        Args:
            html_content: Raw HTML content to convert

        Returns:
            Markdown formatted content
        """
        api_key = self.settings.anthropic_api_key

        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY is not configured")

        # Truncate HTML if too long (Claude has context limits)
        max_html_length = 100000  # ~100KB of HTML
        if len(html_content) > max_html_length:
            logger.warning(
                "HTML content truncated from %d to %d characters",
                len(html_content),
                max_html_length,
            )
            html_content = html_content[:max_html_length]

        prompt = MARKDOWN_CONVERSION_PROMPT + html_content

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-sonnet-4-5",
                    "max_tokens": 8192,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt,
                        }
                    ],
                },
            )

            if response.status_code != 200:
                logger.error("Claude API error: %s", response.text)
                raise Exception(f"Claude API error: {response.status_code}")

            data = response.json()
            content = data.get("content", [])

            if content and len(content) > 0:
                return str(content[0].get("text", ""))

            return ""

    async def scrape_and_convert(self, url: str) -> str:
        """
        Scrape a URL and convert to markdown in one operation.

        Args:
            url: URL to scrape

        Returns:
            Markdown formatted content
        """
        html = await self.scrape_url(url)
        return await self.convert_html_to_markdown(html)
