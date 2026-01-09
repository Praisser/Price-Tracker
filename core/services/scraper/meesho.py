from .base import BaseScraper
import json
import urllib.parse
from core.services.browser import fetch_rendered_html

class MeeshoScraper(BaseScraper):
    """Scraper for Meesho."""
    
    def search(self, query):
        # Meesho Search
        encoded_query = urllib.parse.quote_plus(query)
        url = f"https://www.meesho.com/search?q={encoded_query}"
        
        try:
            # Try regular request first
            response = self.get_page(url)
            html = None
            use_playwright = False
            
            if response:
                if response.status_code == 403:
                     use_playwright = True
                     print("Meesho 403, using Playwright fallback")
                else:
                    html = response.text
            else:
                use_playwright = True
            
            if use_playwright or not html:
                pw = fetch_rendered_html(url)
                if pw and pw.html:
                    html = pw.html
                else:
                    return None

            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            # Look for NEXT_DATA
            script = soup.find('script', id='__NEXT_DATA__')
            if script:
                data = json.loads(script.string)
                
                try:
                    # Generic traversal for Meesho's NEXT_DATA structure
                    # Usually: props -> pageProps -> initialState -> catalogs -> catalogs[0] -> products[0]
                    catalogs = data.get('props', {}).get('pageProps', {}).get('initialState', {}).get('catalogs', {}).get('catalogs', [])
                    
                    if catalogs:
                        # Find first catalog with products
                        for cat in catalogs:
                            products = cat.get('products', [])
                            if products:
                                product = products[0]
                                return {
                                    'website': 'Meesho',
                                    'price': product.get('price'),
                                    'url': "https://www.meesho.com/s/p/" + product.get('slug', ''),
                                    'title': product.get('name')
                                }
                except Exception as e:
                    print(f"Meesho JSON parse error: {e}")
            
        except Exception as e:
            print(f"Meesho scraping error: {e}")
            return None
            
        return None
