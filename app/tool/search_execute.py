import os
import getpass

from app.config import SEARCH_ENGINE, BING_SUBSCRIPTION_KEY, BING_SEARCH_URL


def search(query: str, num_results: int):
    if SEARCH_ENGINE == "baidu":
        from baidusearch.baidusearch import search
        return search(query, num_results=num_results)

    elif SEARCH_ENGINE == "bing":
        from langchain_community.utilities import BingSearchAPIWrapper
        os.environ["BING_SUBSCRIPTION_KEY"] = getpass.getpass(BING_SUBSCRIPTION_KEY)
        os.environ["BING_SEARCH_URL"] = BING_SEARCH_URL
        search = BingSearchAPIWrapper(k=4)
        return search.results(query, num_results=num_results)

    else:
        from googlesearch import search
        return search(query, num_results=num_results)
