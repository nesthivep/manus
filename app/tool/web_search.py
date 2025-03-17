import asyncio
from typing import List

from tenacity import retry, stop_after_attempt, wait_exponential

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
    This function attempts to use the primary search engine API to get up-to-date results.
    If an error occurs, it falls back to an alternative search engine."""
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
        engine_order = self._get_engine_order()
        all_errors = []
        
        for engine_name in engine_order:
            engine = self._search_engine[engine_name]
            try:
                # S'assurer que num_results est un entier
                num_results_int = int(num_results) if not isinstance(num_results, int) else num_results
                
                links = await self._perform_search_with_engine(
                    engine, query, num_results_int
                )
                
                # Vérifier que les résultats sont au bon format
                if links and isinstance(links, list):
                    # Extraire les URLs des résultats (qui peuvent être des dictionnaires)
                    urls = []
                    for item in links:
                        if isinstance(item, dict) and "href" in item:
                            urls.append(item["href"])
                        elif isinstance(item, str):
                            urls.append(item)
                    
                    if urls:  # Si nous avons trouvé des URLs, les retourner
                        return urls
            except Exception as e:
                error_msg = f"Search engine '{engine_name}' failed with error: {e}"
                print(error_msg)
                all_errors.append(error_msg)
        
        # Si tous les moteurs ont échoué, afficher un message d'erreur détaillé
        if all_errors:
            print(f"All search engines failed. Errors: {', '.join(all_errors)}")
        
        return []

    def _get_engine_order(self) -> List[str]:
        """
        Determines the order in which to try search engines.
        Preferred engine is first (based on configuration), followed by the remaining engines.

        Returns:
            List[str]: Ordered list of search engine names.
        """
        preferred = "google"
        if config.search_config and config.search_config.engine:
            preferred = config.search_config.engine.lower()

        engine_order = []
        if preferred in self._search_engine:
            engine_order.append(preferred)
        for key in self._search_engine:
            if key not in engine_order:
                engine_order.append(key)
        return engine_order

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True
    )
    async def _perform_search_with_engine(
        self,
        engine: WebSearchEngine,
        query: str,
        num_results: int,
    ) -> List[str]:
        try:
            # S'assurer que num_results est un entier pour éviter les erreurs de type
            num_results_int = int(num_results) if not isinstance(num_results, int) else num_results
            
            # Définir une fonction qui gère tous les types d'erreurs possibles
            def safe_search():
                try:
                    results = engine.perform_search(query, num_results=num_results_int)
                    # Vérifier si les résultats sont itérables avant de tenter de les convertir en liste
                    if results is None:
                        return []
                    if isinstance(results, (list, tuple)):
                        return list(results)
                    try:
                        # Si c'est un itérable mais pas une liste/tuple, essayer de le convertir
                        return list(results)
                    except:
                        # Si la conversion a échoué, retourner les résultats tels quels s'ils semblent valides
                        if results:
                            return [results]
                        return []
                except TypeError as e:
                    # Gérer explicitement les erreurs de type sans les propager
                    print(f"Type error caught within safe_search: {str(e)}")
                    return []
                except Exception as e:
                    print(f"Error caught within safe_search: {str(e)}")
                    return []
            
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(None, safe_search)
            
            return results
        except Exception as e:
            # Capturer et propager toutes les autres exceptions
            print(f"Unexpected error in _perform_search_with_engine: {str(e)}")
            raise
