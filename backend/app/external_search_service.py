from duckduckgo_search import DDGS
import time


def search_provider_ddg(first, last, state):
    """
    Search for healthcare provider using DuckDuckGo with retry.
    """
    query = f"{first} {last} healthcare {state} USA"
    
    return _search_with_retry(query, max_retries=2)


def _search_with_retry(query: str, max_retries: int = 2) -> list:
    """
    Perform search with automatic retry on failure.
    """
    for attempt in range(max_retries + 1):
        try:
            print(f"  [Search] Query: {query}")
            results = []
            
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=5):
                    result = {
                        "title": r.get("title", ""),
                        "snippet": r.get("body", ""),
                        "link": r.get("href", "")
                    }
                    results.append(result)

            print(f"  [Search] Found {len(results)} results")
            time.sleep(0.3)  # Rate limiting
            return results

        except Exception as e:
            print(f"  [Search] Attempt {attempt + 1} failed: {str(e)}")
            if attempt < max_retries:
                time.sleep(1)  # Wait before retry
                continue
            else:
                return []