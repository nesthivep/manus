import asyncio
from typing import Any, Coroutine, Dict, List

from app.config import config
from app.tool.base import BaseTool
from app.tool.search import (
    BaiduSearchEngine,
    DuckDuckGoSearchEngine,
    GoogleSearchEngine,
    WebSearchEngine,
)


class WebSearch(BaseTool):
    name: str = "web_search"
    description: str = """Perform a web search and return a list of relevant links.
Use this tool when you need to find information on the web, get up-to-date data, or research specific topics.
The tool returns a list of URLs that match the search query.
"""
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "(required) The search query to submit to the search engine.",
            },
            "num_results": {
                "type": "integer",
                "description": "(optional) The number of search results to return. Default is 10.",
                "default": 10,
            },
        },
        "required": ["query"],
    }
    _search_engine: Dict[str, WebSearchEngine] = {
        "google": GoogleSearchEngine(),
        "baidu": BaiduSearchEngine(),
        "duckduckgo": DuckDuckGoSearchEngine(),
    }

    async def execute(self, **kwargs: Any) -> Coroutine[Any, Any, List[str]]:
        """
        Execute a Web search and return a list of URLs.

        Args:
            query (str): The search query to submit to the search engine.
            num_results (int, optional): The number of search results to return. Default is 10.

        Returns:
            Coroutine[Any, Any, List[str]]: A coroutine that returns a list of URLs matching the search query.
        """
        query: str = kwargs.get("query", "")
        num_results: int = kwargs.get("num_results", 10)

        # Run the search in a thread pool to prevent blocking
        loop = asyncio.get_event_loop()
        search_engine = self.get_search_engine()
        links = await loop.run_in_executor(
            None,
            lambda: list(search_engine.perform_search(query, num_results=num_results)),
        )

        # Extract URLs from search results
        urls = [link["url"] for link in links]

        return urls

    def get_search_engine(self) -> WebSearchEngine:
        """Determines the search engine to use based on the configuration."""
        default_engine = self._search_engine.get("google")
        if config.search_config is None:
            return default_engine
        else:
            engine = config.search_config.engine.lower()
            return self._search_engine.get(engine, default_engine)
