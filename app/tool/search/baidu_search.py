from typing import Any

from baidusearch.baidusearch import search

from app.tool.search.base import WebSearchEngine


class BaiduSearchEngine(WebSearchEngine):
    def perform_search(
        self, query: str, num_results: int = 10, *args: Any, **kwargs: Any
    ) -> Any:
        """Baidu search engine."""
        return search(query, num_results=num_results)
