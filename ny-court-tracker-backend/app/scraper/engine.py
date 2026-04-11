"""
Core scraper engine for NY court systems.

Provides HTTP-based scraping with:
- User-Agent rotation (pool of realistic browser UAs)
- Rate limiting (max requests per minute with exponential backoff)
- CAPTCHA detection and graceful fallback
- Randomized timing offsets for stealth
- Cookie/session management
"""

import asyncio
import logging
import random
import time
from dataclasses import dataclass
from typing import Optional

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Pool of realistic User-Agent strings for rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 OPR/109.0.0.0",
]

# Common CAPTCHA indicators in page content
CAPTCHA_INDICATORS = [
    "captcha",
    "recaptcha",
    "g-recaptcha",
    "hCaptcha",
    "challenge-form",
    "please verify you are a human",
    "verify you are not a robot",
    "bot detection",
    "access denied",
    "rate limit exceeded",
    "too many requests",
]

# Cloudflare-specific challenge indicators
CLOUDFLARE_INDICATORS = [
    "_cf_chl_opt",
    "cf-browser-verification",
    "challenge-platform",
    "just a moment",
    "enable javascript and cookies to continue",
    "cf-challenge",
    "cf_chl_managed",
]


@dataclass
class ScrapeResult:
    """Result from a scrape attempt."""
    success: bool
    html: Optional[str] = None
    soup: Optional[BeautifulSoup] = None
    status_code: Optional[int] = None
    error_message: Optional[str] = None
    captcha_detected: bool = False
    cloudflare_detected: bool = False
    response_time_ms: float = 0.0


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    max_requests_per_minute: int = 10
    min_delay_between_requests_sec: float = 2.0
    max_delay_between_requests_sec: float = 8.0
    backoff_multiplier: float = 2.0
    max_backoff_sec: float = 120.0


class ScraperEngine:
    """
    Core scraper engine that handles HTTP requests to court websites.

    Features:
    - User-Agent rotation from a pool of realistic browser UAs
    - Rate limiting with randomized delays between requests
    - CAPTCHA detection with graceful fallback
    - Exponential backoff on errors
    - Cookie/session persistence per court system
    """

    def __init__(self, rate_limit_config: Optional[RateLimitConfig] = None):
        self._rate_limit = rate_limit_config or RateLimitConfig()
        self._last_request_time: float = 0.0
        self._consecutive_errors: int = 0
        self._request_count: int = 0
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client with current User-Agent."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0, connect=10.0),
                follow_redirects=True,
                headers=self._build_headers(),
            )
        return self._client

    def _build_headers(self) -> dict[str, str]:
        """Build request headers with a random User-Agent."""
        ua = random.choice(USER_AGENTS)
        return {
            "User-Agent": ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Cache-Control": "max-age=0",
        }

    async def _apply_rate_limit(self) -> None:
        """Apply rate limiting with randomized delays."""
        now = time.monotonic()
        elapsed = now - self._last_request_time

        # Add randomized delay between requests
        min_delay = self._rate_limit.min_delay_between_requests_sec
        max_delay = self._rate_limit.max_delay_between_requests_sec

        # Apply exponential backoff if we've had consecutive errors
        if self._consecutive_errors > 0:
            backoff = min(
                min_delay * (self._rate_limit.backoff_multiplier ** self._consecutive_errors),
                self._rate_limit.max_backoff_sec,
            )
            min_delay = backoff
            max_delay = backoff * 1.5

        target_delay = random.uniform(min_delay, max_delay)

        if elapsed < target_delay:
            wait_time = target_delay - elapsed
            logger.debug("Rate limiting: waiting %.1f seconds", wait_time)
            await asyncio.sleep(wait_time)

        self._last_request_time = time.monotonic()

    def _detect_captcha(self, html: str) -> bool:
        """Check if the response page contains CAPTCHA indicators."""
        html_lower = html.lower()
        for indicator in CAPTCHA_INDICATORS:
            if indicator.lower() in html_lower:
                logger.warning("CAPTCHA detected: found '%s' in response", indicator)
                return True
        return False

    def _detect_cloudflare(self, html: str) -> bool:
        """Check if the response contains Cloudflare challenge indicators."""
        html_lower = html.lower()
        for indicator in CLOUDFLARE_INDICATORS:
            if indicator.lower() in html_lower:
                logger.warning(
                    "Cloudflare challenge detected: found '%s' in response",
                    indicator,
                )
                return True
        return False

    async def get(self, url: str, params: Optional[dict] = None) -> ScrapeResult:
        """
        Perform a GET request with rate limiting and CAPTCHA detection.

        Args:
            url: The URL to fetch
            params: Optional query parameters

        Returns:
            ScrapeResult with the response data
        """
        await self._apply_rate_limit()

        client = await self._get_client()
        # Rotate User-Agent for each request
        client.headers.update(self._build_headers())

        start_time = time.monotonic()
        try:
            response = await client.get(url, params=params)
            elapsed_ms = (time.monotonic() - start_time) * 1000

            html = response.text
            self._request_count += 1

            # Check for CAPTCHA
            if self._detect_captcha(html):
                self._consecutive_errors += 1
                return ScrapeResult(
                    success=False,
                    html=html,
                    status_code=response.status_code,
                    captcha_detected=True,
                    error_message="CAPTCHA detected on page",
                    response_time_ms=elapsed_ms,
                )

            # Check for Cloudflare challenge
            is_cloudflare = self._detect_cloudflare(html)
            if is_cloudflare:
                self._consecutive_errors += 1
                return ScrapeResult(
                    success=False,
                    html=html,
                    status_code=response.status_code,
                    captcha_detected=True,
                    cloudflare_detected=True,
                    error_message="Cloudflare challenge detected",
                    response_time_ms=elapsed_ms,
                )

            # Check for non-200 status
            if response.status_code != 200:
                self._consecutive_errors += 1
                # Also check if the error page is a Cloudflare challenge
                cf_blocked = self._detect_cloudflare(html)
                return ScrapeResult(
                    success=False,
                    html=html,
                    status_code=response.status_code,
                    captcha_detected=cf_blocked,
                    cloudflare_detected=cf_blocked,
                    error_message=f"HTTP {response.status_code}",
                    response_time_ms=elapsed_ms,
                )

            # Success
            self._consecutive_errors = 0
            soup = BeautifulSoup(html, "lxml")
            return ScrapeResult(
                success=True,
                html=html,
                soup=soup,
                status_code=response.status_code,
                response_time_ms=elapsed_ms,
            )

        except httpx.TimeoutException as e:
            elapsed_ms = (time.monotonic() - start_time) * 1000
            self._consecutive_errors += 1
            logger.error("Timeout scraping %s: %s", url, e)
            return ScrapeResult(
                success=False,
                error_message=f"Timeout: {e}",
                response_time_ms=elapsed_ms,
            )
        except httpx.HTTPError as e:
            elapsed_ms = (time.monotonic() - start_time) * 1000
            self._consecutive_errors += 1
            logger.error("HTTP error scraping %s: %s", url, e)
            return ScrapeResult(
                success=False,
                error_message=f"HTTP error: {e}",
                response_time_ms=elapsed_ms,
            )

    async def post(self, url: str, data: Optional[dict] = None) -> ScrapeResult:
        """
        Perform a POST request (form submission) with rate limiting.

        Args:
            url: The URL to submit to
            data: Form data to submit

        Returns:
            ScrapeResult with the response data
        """
        await self._apply_rate_limit()

        client = await self._get_client()
        client.headers.update(self._build_headers())

        start_time = time.monotonic()
        try:
            response = await client.post(url, data=data)
            elapsed_ms = (time.monotonic() - start_time) * 1000

            html = response.text
            self._request_count += 1

            if self._detect_captcha(html):
                self._consecutive_errors += 1
                return ScrapeResult(
                    success=False,
                    html=html,
                    status_code=response.status_code,
                    captcha_detected=True,
                    error_message="CAPTCHA detected on page",
                    response_time_ms=elapsed_ms,
                )

            # Check for Cloudflare challenge
            is_cloudflare = self._detect_cloudflare(html)
            if is_cloudflare:
                self._consecutive_errors += 1
                return ScrapeResult(
                    success=False,
                    html=html,
                    status_code=response.status_code,
                    captcha_detected=True,
                    cloudflare_detected=True,
                    error_message="Cloudflare challenge detected",
                    response_time_ms=elapsed_ms,
                )

            if response.status_code != 200:
                self._consecutive_errors += 1
                cf_blocked = self._detect_cloudflare(html)
                return ScrapeResult(
                    success=False,
                    html=html,
                    status_code=response.status_code,
                    captcha_detected=cf_blocked,
                    cloudflare_detected=cf_blocked,
                    error_message=f"HTTP {response.status_code}",
                    response_time_ms=elapsed_ms,
                )

            self._consecutive_errors = 0
            soup = BeautifulSoup(html, "lxml")
            return ScrapeResult(
                success=True,
                html=html,
                soup=soup,
                status_code=response.status_code,
                response_time_ms=elapsed_ms,
            )

        except httpx.TimeoutException as e:
            elapsed_ms = (time.monotonic() - start_time) * 1000
            self._consecutive_errors += 1
            logger.error("Timeout posting to %s: %s", url, e)
            return ScrapeResult(
                success=False,
                error_message=f"Timeout: {e}",
                response_time_ms=elapsed_ms,
            )
        except httpx.HTTPError as e:
            elapsed_ms = (time.monotonic() - start_time) * 1000
            self._consecutive_errors += 1
            logger.error("HTTP error posting to %s: %s", url, e)
            return ScrapeResult(
                success=False,
                error_message=f"HTTP error: {e}",
                response_time_ms=elapsed_ms,
            )

    async def health_check(self, url: str) -> bool:
        """Check if a URL is accessible (HEAD request)."""
        try:
            client = await self._get_client()
            response = await client.head(url, follow_redirects=True)
            return response.status_code == 200
        except (httpx.HTTPError, httpx.TimeoutException):
            return False

    async def close(self) -> None:
        """Close the HTTP client and clean up resources."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    @property
    def stats(self) -> dict:
        """Return scraper statistics."""
        return {
            "total_requests": self._request_count,
            "consecutive_errors": self._consecutive_errors,
        }


def get_randomized_offset_minutes(base_minutes: int = 0, max_offset: int = 30) -> int:
    """
    Generate a randomized offset for cron job scheduling.

    Instead of hitting at exactly 6:00 AM, hit at 6:12 AM, 6:47 AM, etc.
    Returns offset in minutes from the base time.
    """
    return base_minutes + random.randint(0, max_offset)
