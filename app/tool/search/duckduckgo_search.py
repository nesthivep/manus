from app.tool.search.base import WebSearchEngine

try:
    from duckduckgo_search import DDGS
except ImportError:
    # Fallback if duckduckgo_search is not installed
    from app.tool.search.google_search import GoogleSearchEngine
    
    class DDGS:
        @staticmethod
        def text(*args, **kwargs):
            print("DuckDuckGo search not available, falling back to Google search")
            return GoogleSearchEngine().perform_search(*args, **kwargs)


class DuckDuckGoSearchEngine(WebSearchEngine):
    
    def perform_search(self, query, num_results = 10, *args, **kwargs):
        """DuckDuckGo search engine."""
        return DDGS.text(query, num_results=num_results)
