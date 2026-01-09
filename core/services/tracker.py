from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail
from core.models import PriceResult, PriceHistory, PriceAlert
from core.services.scraper.amazon import AmazonScraper
from core.services.scraper.flipkart import FlipkartScraper
from core.services.scraper.myntra import MyntraScraper
from core.services.scraper.ajio import AjioScraper
from core.services.scraper.meesho import MeeshoScraper
from core.services.normalizer import normalize_price_data
from core.services.matcher import calculate_match_score
import statistics

def track_prices_for_product(product):
    """
    Scrape prices, apply smart filtering, save results, and check alerts.
    """
    # Safety: Category-based minimum prices to avoid accessories
    # Query keyword -> Minimum price (INR)
    MIN_PRICE_MAP = {
        'macbook': 40000,
        'laptop': 15000,
        'iphone': 30000,
        'ipad': 20000,
        'samsung galaxy s': 30000,
    }
    
    query_lower = product.search_query.lower()
    min_safe_price = 0
    for key, limit in MIN_PRICE_MAP.items():
        if key in query_lower:
            min_safe_price = limit
            break
            
    scrapers = [
        AmazonScraper(),
        FlipkartScraper(),
        MyntraScraper(),
        AjioScraper(),
        MeeshoScraper(),
    ]
    
    raw_results = []
    
    print(f"\n=== Tracking prices for: {product.name} ===")
    
    # Phase 1: Gather Results
    for scraper in scrapers:
        scraper_name = scraper.__class__.__name__.replace('Scraper', '')
        
        try:
            data = scraper.search(product.search_query)
            if data:
                normalized = normalize_price_data(data)
                if normalized:
                    # Initial Score Check
                    score = calculate_match_score(product.search_query, normalized['title'])
                    normalized['match_score'] = score
                    
                    # 1. Hard reject for very low relevance
                    if score < 0.2:
                        print(f"[REJECT] {scraper_name} - Low text match ({score:.2f}): {normalized['title']}")
                        continue
                        
                    # 2. Hard reject for Category Price Floor
                    if normalized['price'] < min_safe_price:
                         print(f"[REJECT] {scraper_name} - Price {normalized['price']} below safety limit {min_safe_price} for '{product.search_query}'")
                         continue
                        
                    raw_results.append(normalized)
                else:
                    print(f"[X] {scraper_name} - Invalid data format")
        except Exception as e:
            print(f"[X] {scraper_name} - Error: {e}")
            continue
            
    if not raw_results:
        return []

    # Phase 2: Price Anomaly Detection (if we have multiple results)
    valid_results = []
    
    if len(raw_results) >= 2:
        prices = [r['price'] for r in raw_results]
        median_price = statistics.median(prices)
        
        # Define Safe Range
        # floor: 20% of median (e.g. 200 for 1000) - catches accessories
        # ceiling: 500% of median (e.g. 5000 for 1000) - catches packs/errors
        price_floor = median_price * 0.2
        price_ceiling = median_price * 5.0
        
        print(f"Stats: Median={median_price}, Floor={price_floor}, Ceiling={price_ceiling}")
        
        for res in raw_results:
            # 1. Check Score Threshold (Standard)
            if res['match_score'] < 0.4:
                print(f"[SKIP] {res['website']} - Score {res['match_score']:.2f} too low")
                continue
                
            # 2. Check Price Anomaly
            if res['price'] < price_floor:
                print(f"[SKIP] {res['website']} - Price anomaly detected (Too low: {res['price']}). Likely accessory.")
                continue
            
            if res['price'] > price_ceiling:
                print(f"[SKIP] {res['website']} - Price anomaly detected (Too high: {res['price']}).")
                continue
                
            valid_results.append(res)
    else:
        # If only 1 result, we can't do comparative stats, just rely on matcher
        # But be stricter on matcher
        if raw_results:
            res = raw_results[0]
            if res['match_score'] >= 0.5:
                 valid_results.append(res)
            else:
                print(f"[SKIP] {res['website']} - Single result but low score {res['match_score']:.2f}")

    # Phase 3: Save Valid Results
    for result_data in valid_results:
        # 1. Update/Create PriceResult
        existing = PriceResult.objects.filter(
            product=product,
            website=result_data['website']
        ).first()
        
        if not existing:
            PriceResult.objects.create(
                product=product,
                website=result_data['website'],
                price=result_data['price'],
                url=result_data['url'],
                image_url=result_data.get('image_url')
            )
        else:
            existing.price = result_data['price']
            existing.url = result_data['url']
            existing.scraped_at = timezone.now()
            if result_data.get('image_url'):
                existing.image_url = result_data['image_url']
            existing.save()
        
        # 2. Log History
        PriceHistory.objects.create(
            product=product,
            website=result_data['website'],
            price=result_data['price']
        )
        
        # 3. Check Alerts
        check_alerts(product, result_data['price'], result_data['url'])
        
    return valid_results


def check_alerts(product, current_price, url):
    """
    Check if current price triggers any active alerts for the product.
    Sends email if threshold is met.
    """
    alerts = PriceAlert.objects.filter(product=product, is_active=True, target_price__gte=current_price)
    
    for alert in alerts:
        subject = f"Price Alert: {product.name} is now ₹{current_price}!"
        message = f"""
        Good news!
        
        The price for "{product.name}" has dropped to ₹{current_price}, which is below your target of ₹{alert.target_price}.
        
        Grab it here: {url}
        
        Cheers,
        Price Tracker
        """
        
        try:
            send_mail(
                subject,
                message,
                settings.EMAIL_HOST_USER,
                [alert.email],
                fail_silently=False,
            )
            print(f"Email sent to {alert.email}")
            
            # Deactivate alert after sending
            alert.is_active = False
            alert.save()
        except Exception as e:
            print(f"Failed to send email to {alert.email}: {e}")
