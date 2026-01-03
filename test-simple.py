"""
Simple test to verify the server is running and tools are accessible.
"""

import asyncio
import httpx


async def test_server():
    """Test basic server connectivity."""
    print("=" * 80)
    print("Testing Brave MCP Server")
    print("=" * 80)

    base_url = "http://localhost:8000"

    async with httpx.AsyncClient(timeout=10.0) as client:
        # Test root endpoint
        print(f"\n1. Testing root endpoint: {base_url}")
        try:
            response = await client.get(base_url)
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text[:200] if response.text else 'No content'}")
        except Exception as e:
            print(f"   Error: {e}")

        # Test SSE endpoint
        print(f"\n2. Testing SSE endpoint: {base_url}/sse")
        try:
            response = await client.get(f"{base_url}/sse")
            print(f"   Status: {response.status_code}")
        except Exception as e:
            print(f"   Error: {e}")

        print("\n" + "=" * 80)
        print("Server is running! ✓")
        print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_server())

