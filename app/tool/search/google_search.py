from googlesearch import search

from app.tool.search.base import WebSearchEngine


class GoogleSearchEngine(WebSearchEngine):
    def perform_search(self, query, num_results=10, *args, **kwargs):
        """Google search engine."""
        try:
            # S'assurer que num_results est un entier
            num_results_int = int(num_results)
            # Ajouter des paramètres par défaut pour éviter les erreurs
            results = list(search(query, num_results=num_results_int, lang="fr", advanced=False))
            # Convertir en format attendu - liste de dictionnaires avec au moins une URL
            formatted_results = []
            for url in results:
                formatted_results.append({"href": url, "title": url})
            return formatted_results
        except Exception as e:
            # Afficher l'erreur pour le débogage
            print(f"Google search error: {str(e)}")
            return []
