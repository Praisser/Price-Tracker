"""
Price comparison service to find the best deal.
"""


def find_best_price(price_results):
    """
    Find the best (lowest) price from a list of price results.
    
    Args:
        price_results: List of PriceResult objects or dicts with 'price' key
        
    Returns:
        dict: Best price result with 'is_best' flag added, or None
    """
    if not price_results:
        return None
    
    # Convert to list if needed
    results = list(price_results)
    
    # Find minimum price
    min_price = None
    best_result = None
    
    for result in results:
        if isinstance(result, dict):
            price = result.get('price')
        else:
            price = result.price
        
        if price is not None:
            if min_price is None or price < min_price:
                min_price = price
                best_result = result
    
    return best_result


def sort_by_price(price_results, ascending=True):
    """
    Sort price results by price.
    
    Args:
        price_results: List of PriceResult objects or dicts
        ascending: Sort order (True for lowest first)
        
    Returns:
        list: Sorted results
    """
    if not price_results:
        return []
    
    def get_price(result):
        if isinstance(result, dict):
            return result.get('price', float('inf'))
        return result.price or float('inf')
    
    sorted_results = sorted(price_results, key=get_price, reverse=not ascending)
    return sorted_results
