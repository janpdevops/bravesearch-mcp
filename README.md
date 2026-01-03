# Brave Web MCP Server

A Model Context Protocol (MCP) server that provides web search and content fetching capabilities using the Brave Search API and web scraping. Built with FastMCP in Python.

## Features

- **Brave Search**: Search the web using Brave's privacy-focused search API
- **Web Fetch**: Retrieve and parse web page content with structured extraction
- **Wikipedia**: Fetch Wikipedia articles via official REST API (supports multiple languages)
- **FastMCP Server**: HTTP-based MCP server running on port 8000

## Tools

### 1. `brave_search`
Search the web using Brave Search API.

**Parameters:**
- `query` (string, required): Search query
- `max_results` (integer, optional, default: 10): Maximum number of results (1-100)

**Returns:**
```json
{
  "query": "example search",
  "results": [
    {
      "title": "Result Title",
      "url": "https://example.com",
      "description": "Result description..."
    }
  ],
  "count": 10
}
```

### 2. `fetch`
Retrieve and parse web content from a URL.

**Parameters:**
- `url` (string, required): Target URL to fetch

**Returns:**
```json
{
  "url": "https://example.com",
  "title": "Page Title",
  "meta_description": "Page description",
  "headings": {
    "h1": ["Main Heading"],
    "h2": ["Subheading 1", "Subheading 2"]
  },
  "links": [
    {"text": "Link Text", "href": "https://example.com/page"}
  ],
  "text_content": "Main page content..."
}
```

### 3. `wikipedia`
Fetch Wikipedia article content via official REST API.

**Parameters:**
- `title` (string, required): Wikipedia article title (e.g., "Python (programming language)")
- `language` (string, optional, default: "en"): Wikipedia language code (e.g., "en", "de", "fr", "es")

**Returns:**
```json
{
  "title": "Article Title",
  "extract": "Article summary/introduction text...",
  "description": "Short description",
  "url": "https://en.wikipedia.org/wiki/Article_Title",
  "thumbnail": {
    "source": "https://upload.wikimedia.org/.../image.jpg",
    "width": 320,
    "height": 427
  },
  "language": "en",
  "type": "standard",
  "coordinates": {
    "lat": 51.5074,
    "lon": -0.1278
  }
}
```

**Note:** The Wikipedia API is preferred over web scraping as requested by Wikipedia. It provides clean, structured data without violating their robots.txt policy.

## Prerequisites

- Python 3.8 or higher
- Brave Search API key (get one at https://brave.com/search/api/)

## Installation

1. **Clone the repository:**
```bash
git clone <repository-url>
cd brave-web-mcp
```

2. **Create a virtual environment:**
```bash
python -m venv venv
```

3. **Activate the virtual environment:**
   - Linux/Mac:
     ```bash
     source venv/bin/activate
     ```
   - Windows:
     ```bash
     venv\Scripts\activate
     ```

4. **Install dependencies:**
```bash
pip install -r requirements.txt
```

5. **Configure environment variables:**
```bash
cp .env.example .env
```

Edit `.env` and add your Brave API key:
```
BRAVE_API_KEY=your_brave_api_key_here
SAFE_SEARCH=Moderate
LOG_LEVEL=DEBUG
```

## Usage

### Running the Server

Start the MCP server:
```bash
python main.py
```

The server will start on port 8000 and be accessible via:
- HTTP endpoint: `http://localhost:8000/mcp`
- SSE endpoint: `http://localhost:8000/sse`

### Using with MCP Clients

Configure your MCP client (e.g., Claude Desktop) to connect to the server:

```json
{
  "mcpServers": {
    "brave-web": {
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

## Development

### Project Structure

```
brave-web-mcp/
├── .env                    # Environment variables (not in git)
├── .env.example           # Template for environment setup
├── .gitignore             # Git ignore patterns
├── requirements.txt       # Python dependencies
├── README.md              # This file
├── brave-mcp.py           # MCP server implementation
├── test-websearch.py      # Test script for brave_search tool
├── test-fetch.py          # Test script for fetch tool
├── test-wikipedia.py      # Test script for wikipedia tool
└── plans/                 # Architecture documents
    └── brave-web-mcp-architecture.md
```

### Running Tests

**Direct Function Tests:**
```bash
# Test Brave Search
python test-websearch.py

# Test Web Fetch
python test-fetch.py

# Test Wikipedia API
python test-wikipedia.py
```

**With pytest (if installed):**
```bash
pytest tests/
```

## Debug Mode

The server supports comprehensive debug logging for development and troubleshooting.

### Configuration

In the `.env` file:
```bash
LOG_LEVEL=DEBUG  # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL
```

**Note:** The `LOG_LEVEL` setting only affects the brave-mcp application logs. FastMCP and its dependencies (Redis, HTTP clients) are automatically configured to log only at INFO level or higher to reduce noise in debug mode.

### Debug Features

When `LOG_LEVEL=DEBUG`, the server logs:
- Incoming MCP requests (complete payload)
- Outgoing MCP responses (complete payload)
- Tool invocations with all parameters
- Brave Search API requests and responses
- Wikipedia API requests and responses
- HTTP requests during web fetching
- Complete error stacktraces
- Timing information for operations

**Third-party libraries** (FastMCP, Redis, httpx) log only at INFO, WARNING, and ERROR levels to keep logs clean and focused on application logic.

### Example Debug Output

```
[INFO] 2026-01-03 10:15:23 - __main__ - Application log level: DEBUG
[DEBUG] 2026-01-03 10:15:23 - __main__ - Debug logging enabled for brave-mcp application
[DEBUG] 2026-01-03 10:15:23 - __main__ - Tool 'brave_search' called with query='python clean code', max_results=10
[DEBUG] 2026-01-03 10:15:23 - __main__ - Brave API request: GET https://api.search.brave.com/res/v1/web/search?q=python+clean+code&count=10
[DEBUG] 2026-01-03 10:15:24 - __main__ - Brave API response: 1234 bytes
[DEBUG] 2026-01-03 10:15:24 - __main__ - Tool 'brave_search' returned 10 results
[INFO] 2026-01-03 10:15:24 - fastmcp - Tool call completed successfully
```

### Log Levels by Component

| Component | DEBUG Mode | Production Mode |
|-----------|-----------|-----------------|
| brave-mcp | DEBUG | INFO |
| FastMCP | INFO | INFO |
| Redis/Docket | INFO | INFO |
| httpx/httpcore | WARNING | WARNING |
| uvicorn | INFO | INFO |

### Production Mode

For production deployment, set `LOG_LEVEL=INFO` or `WARNING` to:
- Reduce log volume
- Protect sensitive data from being logged
- Improve performance



1. **API Key Protection**: Never commit your `.env` file to version control
2. **URL Validation**: The fetch tool validates URLs before making requests
3. **Content Limits**: Fetched content is limited to 100KB to prevent memory issues
4. **Timeouts**: All HTTP requests have 30-second timeouts
5. **Error Handling**: Sensitive information is not exposed in error messages

## Error Handling

Both tools include comprehensive error handling for:
- Missing or invalid API keys
- Invalid parameters
- Network failures and timeouts
- HTTP errors (404, 403, etc.)
- Invalid HTML content
- API rate limits

## Deployment

### Docker Deployment (Optional)

Create a `Dockerfile`:
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["python", "brave-mcp.py"]
```

Build and run:
```bash
docker build -t brave-web-mcp .
docker run -p 8000:8000 --env-file .env brave-web-mcp
```

## Troubleshooting

### Server won't start
- Ensure port 8000 is not already in use
- Check that all dependencies are installed
- Verify Python version is 3.8 or higher

### Brave Search returns errors
- Verify your API key is correct in `.env`
- Check your API quota hasn't been exceeded
- Ensure you have internet connectivity

### Fetch tool fails
- Verify the URL is valid and accessible
- Check if the website blocks automated requests
- Ensure the URL uses http or https scheme

## License

Since this project is mainly vibe coded, I not think this code can even be licenced or enforced. 
This is released into public domain. Do whatever you want with it, I can't stop you anyway, can I? 

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

For issues and questions, please open an issue on the repository.

## Code Style
Clean code. Use small functions, meaningful names, type hints, and docstrings. Use small classes to 
encapsulate related functionality.

## Test driven development
Write tests first, then implement functionality to pass the tests. Use pytest for testing. 

## Integration test scripts
This is a bit of a pretentious wording. Just call the server endpoints. 
* The search can be queried with an example, e.g. "What is the best coding practice for clean code in Python?" 
* Test the fetch tool with a known URL, e.g. "https://en.wikipedia.org/wiki/Robert_C._Martin#Clean_Code"
* You can spin up the server and run the test scripts against these, the .env file is already perpared to run the tests.

## Developer hints and api
See the files in source-doc on how to use fastMcp and Brave web search api
The server must stop on KeyboardInterrupt (Ctrl+C) gracefully.