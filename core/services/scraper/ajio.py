from .base import BaseScraper
import json
import urllib.parse

class AjioScraper(BaseScraper):
    """Scraper for Ajio."""
    
    def search(self, query):
        # Ajio API URL
        # They use a specialized API for search
        encoded_query = urllib.parse.quote_plus(query)
        url = f"https://www.ajio.com/api/search/v3"
        
        params = {
            'fields': 'SITE',
            'currentPage': '0',
            'pageSize': '45',
            'format': 'json',
            'query': query,
            'sortBy': 'relevance'
        }
        
        try:
            response = self.get_page(url, params=params)
            if not response:
                return None
                
            data = response.json()
            
            # Traverse: products -> [0]
            try:
                products = data.get('products', [])
                if products:
                    product = products[0]
                    return {
                        'website': 'Ajio',
                        'price': product.get('price', {}).get('value'),
                        'url': f"https://www.ajio.com{product.get('url')}",
                        'title': product.get('name')
                    }
            except (KeyError, IndexError, AttributeError):
                pass
                
        except Exception as e:
            print(f"Ajio scraping error: {e}")
            return None
            
        return None
