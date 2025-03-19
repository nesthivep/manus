from typing import Any, cast

from duckduckgo_search import DDGS

from app.tool.search.base import WebSearchEngine


class DuckDuckGoSearchEngine(WebSearchEngine):
    def perform_search(self, query, num_results=10, *args, **kwargs):
        """DuckDuckGo search engine."""
        return cast(list[Any], list(DDGS().text(query, max_results=num_results)))
