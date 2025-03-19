from googlesearch import search

from app.tool.search.base import WebSearchEngine


class GoogleSearchEngine(WebSearchEngine):
    def perform_search(self, query, num_results=10, *args, **kwargs):
        """Google search engine."""
        res = []
        for it in search(query, num_results=num_results):
            if isinstance(it, str):
                res.append(it)
            else:
                item = {
                    "title": it.title,
                    "link": it.url,
                    "description": it.description,
                }
                res.append(item)
        return res
