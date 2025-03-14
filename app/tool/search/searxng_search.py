import requests
from pydantic import Field
from urllib.parse import urlencode
from datetime import datetime, timedelta
import pytz
import json
import os
import toml
from typing import List, Dict, Any, Optional, ClassVar

from app.tool.search.base import WebSearchEngine


# Load settings from configuration file
def load_config():
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config", "config.toml")
    if os.path.exists(config_path):
        return toml.load(config_path)
    return {}


# Get configuration with default values
CONFIG = load_config()
SEARXNG_CONFIG = CONFIG.get("search", {}).get("searxng", {})
DEFAULT_BASE_URL = SEARXNG_CONFIG.get("base_url", "https://searx.be")
DEFAULT_NUM_RESULTS = SEARXNG_CONFIG.get("num_results", 5)

# Define request headers
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
}


class SearxngSearchEngine(WebSearchEngine):
    base_url: str = DEFAULT_BASE_URL
    headers: Dict[str, str] = DEFAULT_HEADERS.copy()
    
    def __init__(self, **kwargs):
        self.timezone = pytz.timezone("Asia/Shanghai")
        if "base_url" in kwargs:
            self.base_url = kwargs["base_url"]
        if "headers" in kwargs:
            self.headers = kwargs["headers"]
    
    def __replace_time_keywords__(self, query: str) -> str:
        """
        Replace time keywords with specific dates
        """
        now = datetime.now(self.timezone)
        date_mapping = {
            "今年": now.strftime("%Y年"),
            "昨天": (now - timedelta(days=1)).strftime("%Y年%m月%d日"),
            "前天": (now - timedelta(days=2)).strftime("%Y年%m月%d日"),
            "明天": (now + timedelta(days=1)).strftime("%Y年%m月%d日"),
        }
        for keyword, date in date_mapping.items():
            if keyword in query:
                query = query.replace(keyword, date)
        return query

    def __get_time_range__(self, query: str) -> dict:
        """
        Return time range parameters based on time keywords in query
        """
        time_params = {}
        now = datetime.now(self.timezone)
        if "最近" in query:
            time_params["time_range"] = "week"
            time_params["date_from"] = (now - timedelta(days=7)).strftime("%Y-%m-%d")
            time_params["date_to"] = now.strftime("%Y-%m-%d")
        elif "今天" in query:
            time_params["time_range"] = "day"
        return time_params

    def perform_search(self, query: str, num_results: int = DEFAULT_NUM_RESULTS, *args, **kwargs) -> list[dict]:
        """
        Perform a web search using SearxNG and return a list of results.

        Args:
            query (str): The search query to submit to the search engine.
            num_results (int, optional): The number of search results to return. Default is from config.
            args: Additional arguments.
            kwargs: Additional keyword arguments.

        Returns:
            list[dict]: A list of dictionaries matching the search query.
        """
        processed_query = self.__replace_time_keywords__(query)
        
        # Execute HTTP request synchronously to avoid event loop issues
        results = []
        params = {
            "q": processed_query,
            "format": "json",
            "pageno": 1,
            "language": "zh-CN",
            "categories": "general",
            "no-cache": True,
            "num_pages": 1,
            "results_per_page": max(20, num_results),
            "safesearch": 0,
            "engine_filters": "bing,google",
        }
        
        # Add time range parameters
        time_params = self.__get_time_range__(processed_query)
        params.update(time_params)
        
        try:
            search_url = f"{self.base_url}/search?{urlencode(params)}"
            print(f"Sending request to SearxNG: {search_url}")
            response = requests.get(search_url, headers=self.headers, timeout=10)
            
            # Check response status
            if response.status_code != 200:
                print(f"SearxNG search request failed: {response.status_code}")
                print(f"Response content: {response.text[:500]}")  # Print partial response for diagnosis
                return []
                
            data = response.json()
            if "results" in data:
                for result in data["results"]:
                    full_content = []
                    if result.get("title"):
                        full_content.append(result["title"])
                    if result.get("content"):
                        full_content.append(result["content"])
                    if result.get("summary"):
                        full_content.append(result["summary"])
                    # Extended parameters
                    if result.get("tags"):
                        full_content.append("Tags: " + ", ".join(result["tags"]))
                    if result.get("published_date"):
                        full_content.append("Published on: " + result["published_date"])
                    # Handle other content types
                    if result.get("media_type") == "video":
                        full_content.append("Video link: " + result.get("url", ""))
                    # Add image links
                    if result.get("image_url"):
                        full_content.append("Image link: " + result["image_url"])
                    full_content = list(dict.fromkeys(full_content))
                    result_dict = {
                        "query": processed_query,
                        "title": result.get("title", ""),
                        "link": result.get("url", ""),
                        "snippet": " · ".join(full_content),
                        "source": result.get("engine", ""),
                        "score": result.get("score", 0),
                    }
                    results.append(result_dict)
                
                # Sort by score
                results.sort(key=lambda x: x["score"], reverse=True)
                
                # Limit number of results
                if num_results > 0 and len(results) > num_results:
                    results = results[:num_results]
                    
        except Exception as e:
            print(f"SearxNG search error: {str(e)}")
            import traceback
            print(f"Detailed error: {traceback.format_exc()}")
            
        print(f"Number of search results: {len(results)}")
        return results
