import asyncio
from duckduckgo_search import DDGS

from app.tool.search.base import WebSearchEngine


class DuckDuckGoSearchEngine(WebSearchEngine):
    async def perform_search(self, query, num_results=10, *args, **kwargs):
        """DuckDuckGo search engine."""
        # Run the search in a thread pool to prevent blocking
        loop = asyncio.get_event_loop()
        try:
            results = await loop.run_in_executor(
                None, 
                lambda: list(DDGS().text(query, max_results=num_results))
            )
            return results
        except Exception as e:
            # Return a descriptive error message
            return [f"DuckDuckGo search error: {str(e)}"]
