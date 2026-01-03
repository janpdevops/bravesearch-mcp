"""
Test script for wikipedia tool.

This script tests the wikipedia tool by fetching content from Wikipedia REST API.
The server runs on http://localhost:8000/sse but we test the function directly.
"""

import asyncio
import json
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import httpx
from typing import Dict, Any


class WikipediaClient:
    """Client for fetching Wikipedia content via REST API."""

    def __init__(self):
        """Initialize Wikipedia client."""
        self.client = httpx.AsyncClient(
            timeout=30.0,
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
        """
        # Clean up title (replace spaces with underscores)
        clean_title = title.replace(' ', '_')

        url = f"https://{language}.wikipedia.org/api/rest_v1/page/summary/{clean_title}"

        print(f"Fetching from: {url}")

        response = await self.client.get(url)

        if response.status_code == 404:
            raise ValueError(f"Wikipedia article not found: {title}")

        response.raise_for_status()
        data = response.json()

        return self._format_article(data)

    def _format_article(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Format Wikipedia API response."""
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


async def test_wikipedia():
    """Test the wikipedia tool."""
    print("=" * 80)
    print("Testing wikipedia tool (Direct Function Call)")
    print("=" * 80)

    # Test articles
    test_cases = [
        {
            "title": "Robert C. Martin",
            "language": "en",
            "description": "Clean Code author"
        },
        {
            "title": "Python (Programmiersprache)",
            "language": "de",
            "description": "Python in German"
        }
    ]

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n--- Test Case {i}: {test_case['description']} ---")
        print(f"Title: {test_case['title']}")
        print(f"Language: {test_case['language']}")
        print("\n" + "-" * 80)

        try:
            # Create client and fetch article
            client = WikipediaClient()
            result = await client.get_article(
                test_case['title'],
                test_case['language']
            )
            await client.close()

            print("\nResponse received:")
            # Print formatted result
            result_copy = json.loads(json.dumps(result))
            if 'extract' in result_copy and len(result_copy['extract']) > 500:
                result_copy['extract'] = result_copy['extract'][:500] + "... [truncated]"

            print(json.dumps(result_copy, indent=2, ensure_ascii=False))
            print("\n" + "-" * 80)

            # Display results in a readable format
            print(f"\n✓ Wikipedia fetch completed successfully!")
            print(f"Title: {result.get('title', 'N/A')}")
            print(f"Description: {result.get('description', 'No description')}")
            print(f"URL: {result.get('url', 'N/A')}")
            print(f"Language: {result.get('language', 'N/A')}")
            print(f"Type: {result.get('type', 'N/A')}")

            if result.get('thumbnail'):
                print(f"\nThumbnail:")
                print(f"  Source: {result['thumbnail']['source']}")
                print(f"  Size: {result['thumbnail']['width']}x{result['thumbnail']['height']}")

            if result.get('coordinates'):
                print(f"\nCoordinates:")
                print(f"  Latitude: {result['coordinates']['lat']}")
                print(f"  Longitude: {result['coordinates']['lon']}")

            extract = result.get('extract', '')
            print(f"\nExtract ({len(extract)} characters):")
            print(f"{extract[:400]}...")

        except ValueError as e:
            print(f"\n✗ Article not found: {str(e)}")
        except httpx.HTTPStatusError as e:
            print(f"\n✗ HTTP Error: {e.response.status_code}")
            print(f"Response: {e.response.text}")
        except httpx.RequestError as e:
            print(f"\n✗ Request Error: {str(e)}")
        except Exception as e:
            print(f"\n✗ Unexpected Error: {str(e)}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 80)
    print("✓ All tests completed!")
    print("=" * 80)


if __name__ == "__main__":
    print("\nWikipedia Tool Test Script (Direct Function Test)\n")
    print("Server runs on: http://localhost:8000/sse")
    print("This test calls the Wikipedia REST API directly.\n")
    asyncio.run(test_wikipedia())

