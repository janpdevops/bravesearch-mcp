"""
Test script for fetch tool.

This script tests the fetch tool by retrieving content from a Wikipedia page.
The server runs on http://localhost:8000/sse but we test the function directly.
"""

import asyncio
import json
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import httpx
from bs4 import BeautifulSoup


class WebFetcher:
    """Client for fetching and parsing web content."""

    def __init__(self):
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
        )
        self.max_content_size = 100_000  # 100KB limit

    async def fetch(self, url: str):
        """Fetch and parse a URL."""
        # Validate URL
        if not url.startswith(('http://', 'https://')):
            raise ValueError("URL must start with http:// or https://")

        # Fetch the page
        response = await self.client.get(url, follow_redirects=True)
        response.raise_for_status()

        # Check content size
        content = response.text
        if len(content) > self.max_content_size:
            content = content[:self.max_content_size]

        # Parse with BeautifulSoup
        soup = BeautifulSoup(content, 'html.parser')

        # Extract information
        result = {
            "url": str(response.url),
            "title": soup.title.string if soup.title else "No title",
            "meta_description": "",
            "headings": {},
            "links": [],
            "text_content": ""
        }

        # Meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            result["meta_description"] = meta_desc['content']

        # Headings
        for tag in ['h1', 'h2', 'h3']:
            headings = [h.get_text(strip=True) for h in soup.find_all(tag)]
            if headings:
                result["headings"][tag] = headings

        # Links
        for link in soup.find_all('a', href=True)[:50]:  # Limit to 50 links
            href = link['href']
            text = link.get_text(strip=True)
            if href and text:
                result["links"].append({"text": text, "href": href})

        # Text content
        for script in soup(['script', 'style']):
            script.decompose()
        result["text_content"] = soup.get_text(separator=' ', strip=True)

        return result

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


async def test_fetch():
    """Test the fetch tool."""
    print("=" * 80)
    print("Testing fetch tool (Direct Function Call)")
    print("=" * 80)

    # FastMcp welcome page
    test_url = "https://gofastmcp.com/getting-started/welcome"

    print(f"\nTarget URL: {test_url}")
    print("\n" + "-" * 80)

    try:
        # Create fetcher and execute fetch
        fetcher = WebFetcher()
        result = await fetcher.fetch(test_url)
        await fetcher.close()

        print("\nResponse received (truncated):")
        # Print a truncated version for readability
        result_copy = json.loads(json.dumps(result))
        if 'text_content' in result_copy:
            result_copy['text_content'] = result_copy['text_content'][:500] + "... [truncated]"
        if 'links' in result_copy and len(result_copy['links']) > 10:
            result_copy['links'] = result_copy['links'][:10] + [{"note": f"... and {len(result_copy['links']) - 10} more links"}]

        print(json.dumps(result_copy, indent=2))
        print("\n" + "-" * 80)

        # Display results in a readable format
        print(f"\n✓ Fetch completed successfully!")
        print(f"URL: {result.get('url', 'N/A')}")
        print(f"Title: {result.get('title', 'No title')}")
        print(f"Meta Description: {result.get('meta_description', 'No description')[:150]}...")

        headings = result.get('headings', {})
        if headings:
            print(f"\nHeadings found:")
            for tag, texts in headings.items():
                print(f"  {tag.upper()}: {len(texts)} heading(s)")
                if texts:
                    print(f"    First: {texts[0][:80]}")

        links = result.get('links', [])
        print(f"\nLinks found: {len(links)}")
        if links:
            print(f"  Sample links (first 3):")
            for link in links[:3]:
                print(f"    - {link.get('text', 'No text')[:50]}")
                print(f"      {link.get('href', 'No URL')[:80]}")

        text_content = result.get('text_content', '')
        print(f"\nText content length: {len(text_content)} characters")
        print(f"Preview: {text_content[:300]}...")

        print("\n" + "=" * 80)
        print("✓ Test completed successfully!")
        print("=" * 80)

    except httpx.HTTPStatusError as e:
        print(f"\n✗ HTTP Error: {e.response.status_code}")
        print(f"Response: {e.response.text}")
        sys.exit(1)
    except httpx.RequestError as e:
        print(f"\n✗ Request Error: {str(e)}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    print("\n Web Fetch Tool Test Script (Direct Function Test)\n")
    print("Server runs on: http://localhost:8000/sse")
    print("This test calls the fetch function directly.\n")
    asyncio.run(test_fetch())

