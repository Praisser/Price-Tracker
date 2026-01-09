from .base import BaseScraper
from bs4 import BeautifulSoup
import urllib.parse
import re

from core.services.browser import fetch_rendered_html


class AmazonScraper(BaseScraper):
    """Scraper for Amazon.in"""
    
    def search(self, query):
        """Search Amazon for the product."""
        try:
            # Amazon search URL
            search_url = "https://www.amazon.in/s"
            params = {
                'k': query,
            }
            
            # Try regular HTTP request first
            response = self.get_page(search_url, params=params)
            html = None
            use_playwright = False
            
            if response:
                # Check status code
                if response.status_code in (429, 503, 502, 403):
                    use_playwright = True
                    print(f"Amazon returned {response.status_code}, using Playwright fallback")
                else:
                    html = response.text
            else:
                # Request failed or returned None - use Playwright
                use_playwright = True
                print("Amazon request failed, using Playwright fallback")

            # If blocked/503 or no HTML, fall back to Playwright-rendered HTML
            if use_playwright or not html or len(html) < 1000:
                print(f"Fetching Amazon with Playwright for: {query}")
                url = f"{search_url}?{urllib.parse.urlencode(params)}"
                pw = fetch_rendered_html(url)
                if pw and pw.html:
                    html = pw.html
                    print(f"Playwright fetched {len(html)} chars from Amazon")
                else:
                    print("Playwright also failed for Amazon")
                    return None
            
            # Try html.parser if lxml fails
            try:
                soup = BeautifulSoup(html, 'html.parser')
            except:
                soup = BeautifulSoup(html, 'lxml')
            
            # Try to find the first product result with multiple strategies
            product = None
            
            # Strategy 1: Look for data-component-type="s-search-result"
            products = soup.find_all('div', {'data-component-type': 's-search-result'})
            if products:
                # Filter out sponsored ads if possible
                for p in products:
                    if not p.find('span', string=re.compile('Sponsored', re.I)):
                        product = p
                        break
                if not product and products:
                    product = products[0]
            
            # Strategy 2: Look for s-result-item class
            if not product:
                products = soup.find_all('div', class_=re.compile('s-result-item'))
                if products:
                    product = products[0]
            
            # Strategy 3: Look for any div with data-asin
            if not product:
                products = soup.find_all('div', {'data-asin': True})
                if products:
                    product = products[0]
            
            if not product:
                return None
            
            # Extract price - try multiple methods
            price = None
            
            # Method 1: a-price-whole
            price_elem = product.find('span', class_='a-price-whole')
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                price = self.parse_price(price_text)
            
            # Method 2: a-offscreen (hidden price)
            if not price:
                price_elem = product.find('span', class_='a-offscreen')
                if price_elem:
                    price_text = price_elem.get_text(strip=True)
                    price = self.parse_price(price_text)
            
            # Method 3: a-price class
            if not price:
                price_elem = product.find('span', class_=re.compile('a-price'))
                if price_elem:
                    # Look for price text in children
                    for child in price_elem.find_all(['span', 'text']):
                        price_text = child.get_text(strip=True)
                        price = self.parse_price(price_text)
                        if price:
                            break
            
            # Method 4: Search for price pattern in text
            if not price:
                price_text = product.get_text()
                # Look for ₹ followed by numbers
                price_match = re.search(r'₹\s*([\d,]+)', price_text)
                if price_match:
                    price = self.parse_price(price_match.group(0))
            
            if not price:
                return None
            
            # Extract product URL
            url = None
            link_elem = product.find('h2', class_=re.compile('a-size-mini|a-size-base'))
            if link_elem:
                link = link_elem.find('a', href=True)
                if link:
                    href = link.get('href', '')
                    if href:
                        if href.startswith('/'):
                            url = f"https://www.amazon.in{href.split('/ref')[0]}"
                        elif href.startswith('http'):
                            url = href.split('/ref')[0]
            
            # Fallback: find any link with /dp/ or /gp/
            if not url:
                link = product.find('a', href=re.compile(r'/dp/|/gp/'))
                if link:
                    href = link.get('href', '')
                    if href.startswith('/'):
                        url = f"https://www.amazon.in{href.split('/ref')[0]}"
                    elif href.startswith('http'):
                        url = href.split('/ref')[0]
            
            if not url:
                return None
            
            # Extract title
            title = None
            title_elem = product.find('h2', class_=re.compile('a-size-mini|a-size-base'))
            if title_elem:
                title_span = title_elem.find('span')
                if title_span:
                    title = title_span.get_text(strip=True)
                else:
                    title = title_elem.get_text(strip=True)
            
            # Extract image URL
            image_url = None
            img_elem = product.find('img', class_='s-image')
            if img_elem:
                image_url = img_elem.get('src')

            if url and price:
                return {
                    'website': 'Amazon',
                    'price': price,
                    'url': url,
                    'title': title or query,
                    'image_url': image_url
                }
        except Exception as e:
            print(f"Amazon scraper error: {e}")
        
        return None
