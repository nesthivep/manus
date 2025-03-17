from typing import Any, Dict, List

from duckduckgo_search import DDGS

from app.tool.search.base import WebSearchEngine


class DuckDuckGoSearchEngine(WebSearchEngine):
    async def perform_search(
        self, query: str, num_results: int = 10, *args: Any, **kwargs: Any
    ) -> List[Dict[str, Any]]:
        """DuckDuckGo search engine."""
        results = await DDGS().text(query, max_results=num_results)
        return results
