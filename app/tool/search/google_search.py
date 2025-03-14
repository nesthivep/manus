import asyncio
from googlesearch import search

from app.tool.search.base import WebSearchEngine


class GoogleSearchEngine(WebSearchEngine):
    async def perform_search(self, query, num_results=10, *args, **kwargs):
        """Google search engine."""
        # Run the search in a thread pool to prevent blocking
        loop = asyncio.get_event_loop()
        try:
            results = await loop.run_in_executor(
                None, 
                lambda: list(search(query, num_results=num_results))
            )
            return results
        except Exception as e:
            # Return a descriptive error message
            return [f"Google search error: {str(e)}"]
