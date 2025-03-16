from typing import Any

from duckduckgo_search import DDGS

from app.tool.search.base import WebSearchEngine


class DuckDuckGoSearchEngine(WebSearchEngine):
    async def perform_search(
        self, query: str, num_results: int = 10, *args: Any, **kwargs: Any
    ) -> list[dict[str, Any]]:
        """DuckDuckGo search engine."""
        return await DDGS().text(query, num_results=num_results)
