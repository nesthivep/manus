import asyncio
import os
import tomllib
from typing import List, Dict

from app.tool.base import BaseTool
from app.config import config
from app.tool.search import WebSearchEngine, BaiduSearchEngine, GoogleSearchEngine, DuckDuckGoSearchEngine, SearxngSearchEngine


def load_toml_config():
    """Load configuration directly from the config file"""
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    config_path = os.path.join(root_dir, "config", "config.toml")
    if os.path.exists(config_path):
        with open(config_path, "rb") as f:
            return tomllib.load(f)
    return {}


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
    
    # Lazy initialization of search engines to ensure latest configuration is used
    @property
    def _search_engine(self) -> Dict[str, WebSearchEngine]:
        """Get search engine instances, ensuring the latest configuration is used each time"""
        # Load SearxNG configuration directly from config file
        raw_config = load_toml_config()
        searxng_base_url = None
        
        if "search" in raw_config and "searxng" in raw_config["search"]:
            searxng_config = raw_config["search"]["searxng"]
            if "base_url" in searxng_config:
                searxng_base_url = searxng_config["base_url"]
                print(f"Loaded SearxNG base_url from config: {searxng_base_url}")
        
        # Create search engine instances
        engines = {
            "google": GoogleSearchEngine(),
            "baidu": BaiduSearchEngine(),
            "duckduckgo": DuckDuckGoSearchEngine(),
        }
        
        # Only create SearxNG search engine instance if base_url is found in config
        if searxng_base_url:
            engines["searxng"] = SearxngSearchEngine(base_url=searxng_base_url)
        
        return engines

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
        loop = asyncio.get_event_loop()
        search_engine = self.get_search_engine()
        print(f"Using search engine: {type(search_engine).__name__}")
        if hasattr(search_engine, "base_url"):
            print(f"Search engine base_url: {search_engine.base_url}")
            
        links = await loop.run_in_executor(
            None, lambda: list(search_engine.perform_search(query, num_results=num_results))
        )

        return links

    def get_search_engine(self) -> WebSearchEngine:
        """Determines the search engine to use based on the configuration."""
        default_engine = self._search_engine.get("google")
        if config.search_config is None:
            return default_engine
        else:
            engine = config.search_config.engine.lower()
            return self._search_engine.get(engine, default_engine)
