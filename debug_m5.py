from core.services.tracker import track_prices_for_product
from core.models import Product, PriceResult

def debug_m5():
    query = "MacBook Air M5"
    print(f"--- Debugging '{query}' ---")
    
    # 1. Clear existing data to force fresh scrape
    Product.objects.filter(name__icontains=query).delete()
    print("Cleared existing data.")
    
    # 2. Create product
    product = Product.objects.create(name=query, search_query=query)
    
    # 3. specific check for min_price logic (simulated)
    MIN_PRICE_MAP = {
        'macbook': 40000,
        'laptop': 15000,
        'iphone': 30000,
        'ipad': 20000,
        'samsung galaxy s': 30000,
    }
    query_lower = query.lower()
    min_safe_price = 0
    for key, limit in MIN_PRICE_MAP.items():
        if key in query_lower:
            min_safe_price = limit
            print(f"Matched key '{key}' -> Limit {limit}")
            break
            
    if min_safe_price == 0:
        print("WARNING: No minimum price matched!")
        
    # 4. Run Tracker (this will print [REJECT] or [OK] logs from tracker.py)
    results = track_prices_for_product(product)
    
    print("\n--- Final DB Results ---")
    saved_results = PriceResult.objects.filter(product=product)
    for res in saved_results:
        print(f"[{res.website}] {res.price} - {res.url}")

if __name__ == "__main__":
    debug_m5()
