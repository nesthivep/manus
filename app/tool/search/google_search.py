from typing import Any

from googlesearch import search

from app.tool.search.base import WebSearchEngine


class GoogleSearchEngine(WebSearchEngine):
    def perform_search(
        self, query: str, num_results: int = 10, *args: Any, **kwargs: Any
    ) -> Any:
        """Google search engine."""
        return search(query, num_results=num_results)
