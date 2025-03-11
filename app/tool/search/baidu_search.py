from app.tool.search.base import WebSearchEngine

try:
    from baidusearch.baidusearch import search
except ImportError:
    # Fallback if baidusearch is not installed
    from app.tool.search.google_search import GoogleSearchEngine
    
    def search(*args, **kwargs):
        print("Baidu search not available, falling back to Google search")
        return GoogleSearchEngine().perform_search(*args, **kwargs)


class BaiduSearchEngine(WebSearchEngine):
    
    def perform_search(self, query, num_results = 10, *args, **kwargs):
        """Baidu search engine."""
        return search(query, num_results=num_results)
