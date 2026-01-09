
import sys
import os
import django

# Setup Django environment
sys.path.append('d:\\ProjectIOMP\\Price-Tracker')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'price_tracker.settings')
django.setup()

from core.services.scraper.flipkart import FlipkartScraper

def test_scraper():
    query = "laneige lip sleeping mask"
    print(f"Testing Flipkart scraper with query: '{query}'")
    
    scraper = FlipkartScraper()
    result = scraper.search(query)
    
    if result:
        print("\n--- Result Found ---")
        print(f"Title: {result.get('title')}")
        print(f"Price: {result.get('price')}")
        print(f"URL: {result.get('url')}")
        
        # Check relevance
        title = result.get('title', '').lower()
        if 'laneige' not in title:
            print("\n[FAIL] Relevance Check Failed: 'laneige' not found in title.")
        else:
            print("\n[PASS] Result seems relevant.")
    else:
        print("\nNo result found.")

if __name__ == "__main__":
    test_scraper()
