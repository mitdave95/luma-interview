"""URL scraping routes for converting web pages to markdown."""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl

from luma_api.services.scrape_service import ScrapeService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scrape", tags=["Scraping"])


class ScrapeUrlRequest(BaseModel):
    """Request for scraping a URL using Playwright."""

    url: HttpUrl


class ScrapeResponse(BaseModel):
    """Response containing converted markdown."""

    markdown: str
    url: str | None = None
    source: str


@router.post("/playwright", response_model=ScrapeResponse)
async def scrape_with_playwright(request: ScrapeUrlRequest) -> dict[str, Any]:
    """
    Scrape a URL using Playwright headless browser and convert to markdown.

    This endpoint:
    1. Uses Playwright to render the page with a headless browser
    2. Extracts the HTML content
    3. Sends the HTML to Claude to convert to clean markdown
    """
    scrape_service = ScrapeService()
    url_str = str(request.url)

    try:
        # Scrape URL and convert to markdown
        markdown = await scrape_service.scrape_and_convert(url_str)

        return {
            "markdown": markdown,
            "url": url_str,
            "source": "playwright",
        }

    except Exception as e:
        logger.exception("Error scraping URL: %s", e)
        raise HTTPException(
            status_code=500,
            detail=f"Error scraping URL: {str(e)}",
        )
