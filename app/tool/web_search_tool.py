import asyncio
from typing import List

from app.tool.base import BaseTool
from app.tool.search_execute import search


from app.config import SEARCH_ENGINE


class WebSearch(BaseTool):
    name: str = f"{SEARCH_ENGINE}_search"
    description: str = f"""Perform a {SEARCH_ENGINE} search and return a list of relevant links.
Use this tool when you need to find information on the web, get up-to-date data, or research specific topics.
The tool returns a list of URLs that match the search query.
"""
    parameters: dict = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "(required) The search query to submit to Google.",
            },
            "num_results": {
                "type": "integer",
                "description": "(optional) The number of search results to return. Default is 10.",
                "default": 10,
            },
        },
        "required": ["query"],
    }

    async def execute(self, query: str, num_results: int = 10) -> List[str]:
        """
        Execute a Google search and return a list of URLs.

        Args:
            query (str): The search query to submit to Google.
            num_results (int, optional): The number of search results to return. Default is 10.

        Returns:
            List[str]: A list of URLs matching the search query.
        """

        # Run the search in a thread pool to prevent blocking

        loop = asyncio.get_event_loop()
        links = await loop.run_in_executor(
            None, lambda: list(search(query=query, num_results=num_results))
        )

        return links
