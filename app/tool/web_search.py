import asyncio
from typing import List

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
    parameters: dict = {
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
    _search_engine: dict[str, WebSearchEngine] = {
        "google": GoogleSearchEngine(),
        "baidu": BaiduSearchEngine(),
        "duckduckgo": DuckDuckGoSearchEngine(),
    }

    async def execute(self, query: str, num_results: int = 10) -> List[str]:
        """
        Execute a Web search and return a list of URLs.

        Args:
            query (str): The search query to submit to the search engine.
            num_results (int, optional): The number of search results to return. Default is 10.

        Returns:
            List[str]: A list of URLs matching the search query.
        """
        # Run the search in a thread pool to prevent blocking
        num_results = int(num_results)
        search_engine = self.get_search_engine()
        
        try:
            # Check if the search result is awaitable (coroutine)
            search_result = search_engine.perform_search(query, num_results=num_results)
            
            # If it's a coroutine, await it
            if asyncio.iscoroutine(search_result):
                links = await search_result
            else:
                # If it's already an iterable, convert to list
                links = list(search_result)
                
            # Ensure we always return a list
            if not isinstance(links, list):
                links = [links] if links else []
                
            return links
        except Exception as e:
            # Return a descriptive error message as a list with one item
            error_msg = f"Search error: {str(e)}"
            return [error_msg]

    def get_search_engine(self) -> WebSearchEngine:
        """Determines the search engine to use based on the configuration."""
        default_engine = self._search_engine.get("google")
        if config.search_config is None:
            return default_engine
        else:
            engine = config.search_config.engine.lower()
            return self._search_engine.get(engine, default_engine)
