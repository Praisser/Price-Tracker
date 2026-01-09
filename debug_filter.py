from core.services.matcher import calculate_match_score
from core.services.scraper.amazon import AmazonScraper
from core.services.scraper.flipkart import FlipkartScraper
from core.services.scraper.myntra import MyntraScraper
from core.services.normalizer import normalize_price_data

def test_matcher():
    print("\n--- Testing Matcher Logic ---")
    query = "MacBook Air M3"
    
    cases = [
        "Apple MacBook Air Laptop with M3 chip",
        "Mahetri Unisex Macbook Sleeve",
        "Transparent Cover for MacBook Air",
        "Apple 2024 MacBook Air 13-inch"
    ]
    
    for title in cases:
        score = calculate_match_score(query, title)
        print(f"Query: '{query}' | Title: '{title}' | Score: {score:.2f}")

def test_scrapers():
    print("\n--- Testing Live Scrapers ---")
    query = "MacBook Air M3"
    scrapers = [FlipkartScraper(), MyntraScraper()] # skip amazon for speed/blocking concern
    
    raw_results = []
    
    for scraper in scrapers:
        name = scraper.__class__.__name__
        print(f"Scanning {name}...")
        try:
            data = scraper.search(query)
            if data:
                norm = normalize_price_data(data)
                if norm:
                    score = calculate_match_score(query, norm['title'])
                    print(f"[{name}] Found: {norm['title']} | Price: {norm['price']} | Score: {score:.2f}")
                    raw_results.append((norm, score))
                else:
                    print(f"[{name}] Normalization failed: {data}")
            else:
                print(f"[{name}] No data returned")
        except Exception as e:
            print(f"[{name}] Error: {e}")

if __name__ == "__main__":
    test_matcher()
    test_scrapers()
