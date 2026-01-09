from .base import BaseScraper
import json
import urllib.parse

class MyntraScraper(BaseScraper):
    """Scraper for Myntra."""
    
    def search(self, query):
        # Myntra search URL
        encoded_query = urllib.parse.quote_plus(query)
        url = f"https://www.myntra.com/{encoded_query}"
        
        try:
            # Myntra often returns JSON in a script tag or directly if headers are right
            # But standard requests often get HTML with embedded state
            response = self.get_page(url)
            if not response:
                return None
                
            soup = self.split_soup(response.text)
            
            # Strategy 1: Look for JSON state in script
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string and 'window.__myx = ' in script.string:
                    try:
                        # Extract the JSON part more robustly
                        # Content is usually: window.__myx = { ... };
                        content = script.string
                        start_marker = 'window.__myx = '
                        start_index = content.find(start_marker) + len(start_marker)
                        
                        # Find the end of the JSON object
                        # It usually ends with };
                        # We can try to strip undefined/trailing chars or just parse
                        json_text = content[start_index:].strip()
                        if json_text.endswith(';'):
                            json_text = json_text[:-1]
                        
                        # Sometimes there's extra JS after the object, so we might need to find the matching brace?
                        # For now, let's try strict find of first object end if straightforward parse fails
                        
                        data = json.loads(json_text)
                        
                        # Traverse JSON to find products
                        # usually: data['searchData']['results']['products']
                        try:
                            products = data.get('searchData', {}).get('results', {}).get('products', [])
                            if products:
                                product = products[0] # Best match
                                return {
                                    'website': 'Myntra',
                                    'price': product.get('price') or product.get('discountedPrice'),
                                    'url': f"https://www.myntra.com/{product.get('landingPageUrl')}",
                                    'title': product.get('productName'),
                                    'image_url': product.get('images', [{}])[0].get('src')
                                }
                        except (KeyError, IndexError, AttributeError):
                            pass
                    except json.JSONDecodeError as e:
                       # print(f"Myntra JSON parse error: {e}")
                       pass
            
            # Strategy 2: Fallback to scraping generic list elements (unreliable on Myntra due to React)
            
        except Exception as e:
            print(f"Myntra scraping error: {e}")
            return None
            
        return None

    def split_soup(self, text):
        from bs4 import BeautifulSoup
        return BeautifulSoup(text, 'html.parser')
