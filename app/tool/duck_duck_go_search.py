import time
import asyncio

from functools import wraps
from itertools import islice
from duckduckgo_search import DDGS
from app.tool.base import BaseTool

class DuckDuckGoSearchTool(BaseTool):
    name: str = "duck_duck_go"
    description: str = (
        "Perform a DuckDuckGo search and return a list of relevant links. "
        "Use this tool when you need to find information on the web, get up-to-date data, or research specific topics. "
        "The tool returns a list of URLs that match the search query."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "(required) The search query to submit to DuckDuckGo.",
            },
            "num_results": {
                "type": "integer",
                "description": "(optional) The number of search results to return. Default is 10.",
                "default": 10,
            },
        },
        "required": ["query"],
    }

    async def execute(self, query: str, num_results: int = 10) -> list[str]:
        """
        Execute a search in DuckDuckGo and return a list of URLs.
        """
        loop = asyncio.get_event_loop()
        # Run the search in a thread pool to prevent blocking
        links = await loop.run_in_executor(
            None, lambda: self.get_search_results(query)
        )
        return list(islice(links, num_results))

    @staticmethod
    def retry_search(max_attempts, initial_delay, backoff):
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                delay = initial_delay
                attempt = 0
                result = None
                while attempt < max_attempts:
                    result = func(*args, **kwargs)
                    if result:
                        return result
                    time.sleep(delay)
                    delay *= backoff
                    attempt += 1
                return result
            return wrapper
        return decorator

    @retry_search(max_attempts=5, initial_delay=1, backoff=2)
    def get_search_results(self, query):
        if not query:
            return []
        results = DDGS().text(query)
        return list(results)
