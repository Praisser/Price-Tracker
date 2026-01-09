
import sys
import os
import django

# Setup Django environment
sys.path.append('d:\\ProjectIOMP\\Price-Tracker')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'price_tracker.settings')
django.setup()

from core.models import Product, PriceResult

def clear_cache():
    query = "laneige lip sleeping mask"
    print(f"Clearing cache for: '{query}'")
    
    products = Product.objects.filter(search_query__iexact=query)
    count = products.count()
    
    if count > 0:
        for p in products:
            print(f"Deleting product: {p.name} (ID: {p.id})")
            # Deleting product cascades to PriceResult usually, but let's be safe
            PriceResult.objects.filter(product=p).delete()
            p.delete()
        print("Cache cleared.")
    else:
        print("No cached product found.")

if __name__ == "__main__":
    clear_cache()
