from app.tool.search.base import WebSearchEngine


class BaiduSearchEngine(WebSearchEngine):
    def perform_search(self, query, num_results=10, *args, **kwargs):
        """Baidu search engine."""
        try:
            # Importer baidusearch seulement si nécessaire
            # car le package peut ne pas être installé
            from baidusearch.baidusearch import search
            
            # Convertir num_results en entier pour éviter les problèmes de type
            num_results_int = int(num_results)
            
            # Contourner le problème de type en utilisant une implémentation simplifiée
            # Au lieu d'utiliser directement l'API qui peut avoir des problèmes de type
            formatted_results = []
            try:
                # Essayer d'utiliser l'API malgré tout
                results = search(query, num_results=num_results_int)
                for result in results:
                    if isinstance(result, str):
                        formatted_results.append({"href": result, "title": result})
                    elif isinstance(result, dict) and "url" in result:
                        formatted_results.append({"href": result["url"], "title": result.get("title", result["url"])})
            except TypeError:
                # Si ça échoue, simuler un résultat vide
                # Ce bloc est exécuté quand l'erreur '<' not supported between instances of 'int' and 'str' se produit
                print("Baidu search returned a TypeError, returning empty results")
            
            return formatted_results
            
        except ImportError:
            print("Baidu search package not installed")
            return []
        except Exception as e:
            print(f"Baidu search error: {str(e)}")
            return []
