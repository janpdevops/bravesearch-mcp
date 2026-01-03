"""
Brave Web MCP Server

A Model Context Protocol server providing web search and content fetching
capabilities using Brave Search API and web scraping.
"""

import asyncio
import json
import logging
import os
import signal
import sys
from typing import Any, Dict, List
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from fastmcp import FastMCP
from pydantic import BaseModel, Field, validator

# Load environment variables
load_dotenv()

# Setup logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()

# Configure root logger
logging.basicConfig(
    level=logging.INFO,  # Set root to INFO
    format='[%(levelname)s] %(asctime)s - %(name)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Get logger for our application
logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

# Suppress debug logging from FastMCP and its dependencies
logging.getLogger('fastmcp').setLevel(logging.INFO)
logging.getLogger('docket').setLevel(logging.INFO)
logging.getLogger('redis').setLevel(logging.INFO)
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('httpcore').setLevel(logging.WARNING)
logging.getLogger('uvicorn').setLevel(logging.INFO)
logging.getLogger('uvicorn.access').setLevel(logging.WARNING)

# Log the effective log level for our app
logger.info(f"Application log level: {LOG_LEVEL}")
logger.debug("Debug logging enabled for brave-mcp application")


# Configuration
BRAVE_API_KEY = os.getenv('BRAVE_API_KEY', '')
SAFE_SEARCH = os.getenv('SAFE_SEARCH', 'Moderate')
BRAVE_API_URL = 'https://api.search.brave.com/res/v1/web/search'

# Constants
MAX_CONTENT_SIZE = 100 * 1024  # 100KB
REQUEST_TIMEOUT = 30  # seconds


class BraveSearchParams(BaseModel):
    """Parameters for brave_search tool."""
    query: str = Field(..., description="Search query string")
    max_results: int = Field(10, description="Maximum number of results (1-100)", ge=1, le=100)


class FetchParams(BaseModel):
    """Parameters for fetch tool."""
    url: str = Field(..., description="URL to fetch content from")

    @validator('url')
    def validate_url(cls, v: str) -> str:
        """Validate URL scheme is http or https."""
        parsed = urlparse(v)
        if parsed.scheme not in ('http', 'https'):
            raise ValueError(f"URL must use http or https scheme, got: {parsed.scheme}")
        if not parsed.netloc:
            raise ValueError("URL must have a valid domain")
        return v


class WikipediaParams(BaseModel):
    """Parameters for wikipedia tool."""
    title: str = Field(..., description="Wikipedia article title")
    language: str = Field("en", description="Wikipedia language code (e.g., 'en', 'de', 'fr')")



class BraveSearchClient:
    """Client for interacting with Brave Search API."""

    def __init__(self, api_key: str, safe_search: str = 'Moderate'):
        """
        Initialize Brave Search client.

        Args:
            api_key: Brave API key
            safe_search: Safe search setting (Off, Moderate, Strict)
        """
        self.api_key = api_key
        self.safe_search = safe_search
        self.client = httpx.AsyncClient(timeout=REQUEST_TIMEOUT)

    async def search(self, query: str, count: int = 10) -> Dict[str, Any]:
        """
        Perform a web search using Brave Search API.

        Args:
            query: Search query string
            count: Number of results to return (1-100)

        Returns:
            Dictionary containing search results

        Raises:
            ValueError: If API key is missing
            httpx.HTTPError: If API request fails
        """
        if not self.api_key:
            raise ValueError("BRAVE_API_KEY environment variable is not set")

        headers = {
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip',
            'X-Subscription-Token': self.api_key
        }

        params = {
            'q': query,
            'count': count,
            'safesearch': self.safe_search.lower()
        }

        logger.debug(f"Brave API request: GET {BRAVE_API_URL}?q={query}&count={count}")

        try:
            response = await self.client.get(
                BRAVE_API_URL,
                headers=headers,
                params=params
            )
            response.raise_for_status()
            data = response.json()

            logger.debug(f"Brave API response: {json.dumps(data, indent=2)[:500]}...")

            return self._format_results(query, data, count)

        except httpx.HTTPStatusError as e:
            logger.error(f"Brave API HTTP error: {e.response.status_code} - {e.response.text}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Brave API request error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Brave API unexpected error: {str(e)}", exc_info=True)
            raise

    def _format_results(self, query: str, data: Dict[str, Any], count: int) -> Dict[str, Any]:
        """
        Format Brave API response into standardized structure.

        Args:
            query: Original search query
            data: Raw API response data
            count: Requested number of results

        Returns:
            Formatted search results
        """
        web_results = data.get('web', {}).get('results', [])

        formatted_results = []
        for result in web_results[:count]:
            formatted_results.append({
                'title': result.get('title', ''),
                'url': result.get('url', ''),
                'description': result.get('description', '')
            })

        return {
            'query': query,
            'results': formatted_results,
            'count': len(formatted_results)
        }

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


class WebFetchClient:
    """Client for fetching and parsing web content."""

    def __init__(self):
        """Initialize web fetch client."""
        self.client = httpx.AsyncClient(
            timeout=REQUEST_TIMEOUT,
            follow_redirects=True,
            limits=httpx.Limits(max_connections=10),
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
        )

    async def fetch(self, url: str) -> Dict[str, Any]:
        """
        Fetch and parse web content from URL.

        Args:
            url: URL to fetch

        Returns:
            Dictionary containing parsed content

        Raises:
            httpx.HTTPError: If request fails
            ValueError: If content is too large or invalid
        """
        logger.debug(f"Fetching URL: {url}")

        try:
            response = await self.client.get(url)
            response.raise_for_status()

            # Check content size
            content_length = len(response.content)
            if content_length > MAX_CONTENT_SIZE:
                raise ValueError(
                    f"Content too large: {content_length} bytes (max: {MAX_CONTENT_SIZE})"
                )

            logger.debug(f"Received {content_length} bytes from {url}")

            # Parse HTML
            soup = BeautifulSoup(response.content, 'html.parser')

            result = {
                'url': url,
                'title': self._extract_title(soup),
                'meta_description': self._extract_meta_description(soup),
                'headings': self._extract_headings(soup),
                'links': self._extract_links(soup, url),
                'text_content': self._extract_text(soup)
            }

            logger.debug(f"Parsed content - Title: {result['title']}, Links: {len(result['links'])}")

            return result

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching {url}: {e.response.status_code}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Request error fetching {url}: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching {url}: {str(e)}", exc_info=True)
            raise

    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract page title."""
        title_tag = soup.find('title')
        return title_tag.get_text(strip=True) if title_tag else ''

    def _extract_meta_description(self, soup: BeautifulSoup) -> str:
        """Extract meta description."""
        meta_tag = soup.find('meta', attrs={'name': 'description'})
        if meta_tag and meta_tag.get('content'):
            return meta_tag['content']
        return ''

    def _extract_headings(self, soup: BeautifulSoup) -> Dict[str, List[str]]:
        """Extract all headings (h1-h6)."""
        headings = {}
        for level in range(1, 7):
            tag_name = f'h{level}'
            tags = soup.find_all(tag_name)
            if tags:
                headings[tag_name] = [tag.get_text(strip=True) for tag in tags]
        return headings

    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, str]]:
        """Extract all links from the page."""
        links = []
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            # Convert relative URLs to absolute
            absolute_url = urljoin(base_url, href)
            text = a_tag.get_text(strip=True)
            links.append({
                'text': text,
                'href': absolute_url
            })
        return links

    def _extract_text(self, soup: BeautifulSoup) -> str:
        """Extract main text content from page."""
        # Remove script and style elements
        for script in soup(['script', 'style', 'header', 'footer', 'nav']):
            script.decompose()

        # Get text
        text = soup.get_text(separator=' ', strip=True)

        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)

        return text

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


class WikipediaClient:
    """Client for fetching Wikipedia content via REST API."""

    def __init__(self):
        """Initialize Wikipedia client."""
        self.client = httpx.AsyncClient(
            timeout=REQUEST_TIMEOUT,
            follow_redirects=True,
            headers={
                'User-Agent': 'MCP-Brave-Server/1.0 (https://github.com/your-repo; contact@example.com)',
                'Accept': 'application/json'
            }
        )

    async def get_article(self, title: str, language: str = "en") -> Dict[str, Any]:
        """
        Fetch Wikipedia article content via REST API.

        Args:
            title: Wikipedia article title
            language: Wikipedia language code (default: "en")

        Returns:
            Dictionary containing article content

        Raises:
            httpx.HTTPError: If request fails
            ValueError: If article not found
        """
        # Clean up title (replace spaces with underscores)
        clean_title = title.replace(' ', '_')

        url = f"https://{language}.wikipedia.org/api/rest_v1/page/summary/{clean_title}"

        logger.debug(f"Fetching Wikipedia article: {url}")

        try:
            response = await self.client.get(url)

            if response.status_code == 404:
                raise ValueError(f"Wikipedia article not found: {title}")

            response.raise_for_status()
            data = response.json()

            logger.debug(f"Wikipedia API response for '{title}': {len(str(data))} bytes")

            return self._format_article(data)

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise ValueError(f"Wikipedia article not found: {title}")
            logger.error(f"Wikipedia API HTTP error: {e.response.status_code}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Wikipedia API request error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Wikipedia API unexpected error: {str(e)}", exc_info=True)
            raise

    def _format_article(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format Wikipedia API response.

        Args:
            data: Raw API response

        Returns:
            Formatted article data
        """
        result = {
            'title': data.get('title', ''),
            'extract': data.get('extract', ''),
            'description': data.get('description', ''),
            'url': data.get('content_urls', {}).get('desktop', {}).get('page', ''),
            'thumbnail': None,
            'language': data.get('lang', 'en'),
            'type': data.get('type', 'standard')
        }

        # Add thumbnail if available
        if 'thumbnail' in data:
            result['thumbnail'] = {
                'source': data['thumbnail'].get('source', ''),
                'width': data['thumbnail'].get('width', 0),
                'height': data['thumbnail'].get('height', 0)
            }

        # Add coordinates if available
        if 'coordinates' in data:
            result['coordinates'] = {
                'lat': data['coordinates'].get('lat'),
                'lon': data['coordinates'].get('lon')
            }

        return result

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


# Initialize FastMCP server
mcp = FastMCP("Brave Web MCP Server")

# Initialize clients
brave_client = BraveSearchClient(BRAVE_API_KEY, SAFE_SEARCH)
fetch_client = WebFetchClient()
wikipedia_client = WikipediaClient()

@mcp.tool()
async def brave_search(query: str, max_results: int = 10) -> Dict[str, Any]:
    """
    Search the web using Brave Search API.

    Args:
        query: Search query string
        max_results: Maximum number of results to return (1-100)

    Returns:
        Search results with title, URL, and description for each result
    """
    logger.debug(f"Tool 'brave_search' called with query='{query}', max_results={max_results}")

    try:
        # Validate parameters
        params = BraveSearchParams(query=query, max_results=max_results)

        # Perform search
        result = await brave_client.search(params.query, params.max_results)

        logger.debug(f"Tool 'brave_search' returned {result['count']} results")

        return result

    except Exception as e:
        logger.error(f"Error in brave_search: {str(e)}", exc_info=True)
        raise


@mcp.tool()
async def fetch(url: str) -> Dict[str, Any]:
    """
    Fetch and parse web content from a URL.

    Args:
        url: Target URL to fetch (must use http or https)

    Returns:
        Parsed web content including title, headings, links, and text
    """
    logger.debug(f"Tool 'fetch' called with url='{url}'")

    try:
        # Validate parameters
        params = FetchParams(url=url)

        # Fetch content
        result = await fetch_client.fetch(params.url)

        logger.debug(f"Tool 'fetch' successfully parsed content from {url}")

        return result

    except Exception as e:
        logger.error(f"Error in fetch: {str(e)}", exc_info=True)
        raise


@mcp.tool()
async def wikipedia(title: str, language: str = "en") -> Dict[str, Any]:
    """
    Get Wikipedia article content via REST API.

    Args:
        title: Wikipedia article title (e.g., "Python (programming language)")
        language: Wikipedia language code (default: "en", also supports "de", "fr", "es", etc.)

    Returns:
        Article content including title, extract, description, URL, and optional thumbnail
    """
    logger.debug(f"Tool 'wikipedia' called with title='{title}', language='{language}'")

    try:
        # Validate parameters
        params = WikipediaParams(title=title, language=language)

        # Fetch article
        result = await wikipedia_client.get_article(params.title, params.language)

        logger.debug(f"Tool 'wikipedia' successfully fetched article '{title}'")

        return result

    except Exception as e:
        logger.error(f"Error in wikipedia: {str(e)}", exc_info=True)
        raise


async def cleanup():
    """Cleanup resources on shutdown."""
    logger.info("Shutting down server, cleaning up resources...")
    await brave_client.close()
    await fetch_client.close()
    await wikipedia_client.close()
    logger.info("Cleanup complete")


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    logger.info(f"Received signal {signum}, initiating shutdown...")
    asyncio.create_task(cleanup())
    sys.exit(0)


def main():
    """Main entry point for the MCP server."""
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logger.info("Starting Brave Web MCP Server...")
    logger.info(f"Log level: {LOG_LEVEL}")
    logger.info(f"Safe search: {SAFE_SEARCH}")

    if not BRAVE_API_KEY:
        logger.error("BRAVE_API_KEY environment variable is not set!")
        logger.error("Please set BRAVE_API_KEY in your .env file")
        sys.exit(1)

    logger.info("Brave API key configured")

    try:
        # Run the FastMCP server on port 8000
        logger.info("Server starting on http://localhost:8000")
        mcp.run(transport='sse', host='localhost', port=8000)
    except KeyboardInterrupt:
        logger.info("Received KeyboardInterrupt, shutting down...")
        asyncio.run(cleanup())
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

