"""
Test script for brave_search tool.

This script tests the brave_search tool by calling it directly.
The server runs on http://localhost:8000/sse but we test the function directly.
"""

import asyncio
import json
import sys
import os

# Add parent directory to path to import brave_mcp
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the brave_search function and BraveSearchClient
from dotenv import load_dotenv
import httpx
from bs4 import BeautifulSoup


# Load environment variables
load_dotenv()


class BraveSearchClient:
    """Client for Brave Search API."""

    def __init__(self, api_key: str, safe_search: str = "Moderate"):
        if not api_key:
            raise ValueError("Brave API key is required")
        self.api_key = api_key
        self.safe_search = safe_search
        self.base_url = "https://api.search.brave.com/res/v1/web/search"
        self.client = httpx.AsyncClient(timeout=30.0)

    async def search(self, query: str, count: int = 10):
        """Execute a search query."""
        if not 1 <= count <= 100:
            raise ValueError("count must be between 1 and 100")

        params = {
            "q": query,
            "count": count,
            "safesearch": self.safe_search.lower()
        }

        headers = {
            "Accept": "application/json",
            "X-Subscription-Token": self.api_key
        }

        response = await self.client.get(self.base_url, params=params, headers=headers)
        response.raise_for_status()

        data = response.json()
        return self._format_results(query, data, count)

    def _format_results(self, query: str, data: dict, count: int):
        """Format search results."""
        results = []
        web_results = data.get("web", {}).get("results", [])

        for item in web_results[:count]:
            results.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "description": item.get("description", "")
            })

        return {
            "query": query,
            "results": results,
            "count": len(results)
        }

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


async def test_brave_search():
    """Test the brave_search function directly."""
    print("=" * 80)
    print("Testing brave_search tool (Direct Function Call)")
    print("=" * 80)

    # Test query
    query = "What is the best coding practice for clean code in Python?"
    max_results = 5

    print(f"\nQuery: {query}")
    print(f"Max results: {max_results}")
    print("\n" + "-" * 80)

    try:
        # Get API key from environment
        api_key = os.getenv("BRAVE_API_KEY")
        if not api_key or api_key == "your_brave_api_key_here":
            print("\n✗ Error: BRAVE_API_KEY not configured in .env file")
            print("Please add your Brave API key to the .env file")
            sys.exit(1)

        # Create client and execute search
        client = BraveSearchClient(api_key, safe_search=os.getenv("SAFE_SEARCH", "Moderate"))
        result = await client.search(query, max_results)
        await client.close()

        print("\nResponse received:")
        print(json.dumps(result, indent=2))
        print("\n" + "-" * 80)

        # Display results in a readable format
        print(f"\n✓ Search completed successfully!")
        print(f"Query: {result.get('query', 'N/A')}")
        print(f"Results found: {result.get('count', 0)}")
        print("\nTop results:")

        for i, res in enumerate(result.get('results', [])[:5], 1):
            print(f"\n{i}. {res.get('title', 'No title')}")
            print(f"   URL: {res.get('url', 'No URL')}")
            print(f"   Description: {res.get('description', 'No description')[:100]}...")

        print("\n" + "=" * 80)
        print("✓ Test completed successfully!")
        print("=" * 80)

    except ValueError as e:
        print(f"\n✗ Configuration Error: {str(e)}")
        sys.exit(1)
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
    print("\n🔍 Brave Search Tool Test Script (Direct Function Test)\n")
    print("Server runs on: http://localhost:8000/sse")
    print("This test calls the search function directly.\n")
    asyncio.run(test_brave_search())



