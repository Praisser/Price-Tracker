from .base import BaseScraper
from bs4 import BeautifulSoup
import urllib.parse
import re

from core.services.browser import fetch_rendered_html


class FlipkartScraper(BaseScraper):
    """Scraper for Flipkart.com"""
    
    def search(self, query):
        """Search Flipkart for the product."""
        try:
            # Flipkart search URL
            search_url = "https://www.flipkart.com/search"
            params = {
                'q': query
            }
            
            # Try regular HTTP request first
            response = self.get_page(search_url, params=params)
            html = None
            use_playwright = False
            
            if response:
                # Check status code
                if response.status_code in (429, 503, 502, 403):
                    use_playwright = True
                    print(f"Flipkart returned {response.status_code}, using Playwright fallback")
                else:
                    html = response.text
            else:
                # Request failed - use Playwright
                use_playwright = True
                print("Flipkart request failed, using Playwright fallback")

            # If blocked or no HTML, fall back to Playwright
            if use_playwright or not html or len(html) < 1000:
                print(f"Fetching Flipkart with Playwright for: {query}")
                url = f"{search_url}?{urllib.parse.urlencode(params)}"
                pw = fetch_rendered_html(url)
                if pw and pw.html:
                    html = pw.html
                    print(f"Playwright fetched {len(html)} chars from Flipkart")
                else:
                    print("Playwright also failed for Flipkart")
                    return None
            
            # Try html.parser if lxml fails
            try:
                soup = BeautifulSoup(html, 'html.parser')
            except:
                soup = BeautifulSoup(html, 'lxml')
            
            # Find all potential product cards
            candidates = []
            
            # Strategy 1: Look for divs with data-id attribute (Standard Flipkart Grid/List)
            products = soup.find_all('div', {'data-id': True})
            
            if not products:
                # Strategy 2: Look for common product containers if data-id missing
                # Try to find containers with links that look like products
                links = soup.find_all('a', href=re.compile(r'/p/'))
                seen_parents = set()
                for link in links:
                    parent = link.find_parent('div')
                    if parent and parent not in seen_parents:
                        products.append(parent)
                        seen_parents.add(parent)
            
            # Iterate through top 40 candidates to find the best match (Ads can push real results down)
            for product in products[:40]:
                try:
                    # Extract title
                    title = None
                    title_elem = product.find('div', class_=re.compile('_4rR01T|s1Q9rs|IRpwTa'))
                    if title_elem:
                        title = title_elem.get_text(strip=True)
                    else:
                        # Fallback title from image alt or link
                        img = product.find('img', alt=True)
                        if img:
                            title = img['alt']
                        else:
                            # Try link text
                            link = product.find('a', href=re.compile(r'/p/'))
                            if link:
                                title = link.get_text(strip=True)
                    
                    if not title:
                        continue
                        
                    # Extract Price
                    price = None
                    price_elem = product.find('div', class_=re.compile('_30jeq3'))
                    if price_elem:
                        price = self.parse_price(price_elem.get_text(strip=True))
                    
                    if not price:
                        # Fallback price regex
                        price_match = re.search(r'₹\s*([\d,]+)', product.get_text())
                        if price_match:
                            price = self.parse_price(price_match.group(0))
                            
                    if not price:
                        continue
                        
                    # Extract URL
                    url = None
                    link = product.find('a', href=re.compile(r'/p/'))
                    if link:
                        href = link.get('href', '')
                        if href.startswith('/'):
                            url = f"https://www.flipkart.com{href.split('?')[0]}"
                        elif href.startswith('http'):
                            url = href.split('?')[0]
                            
                    if not url:
                        continue
                        
                    # Extract image
                    image_url = None
                    img = product.find('img', src=True)
                    if img:
                        image_url = img['src']

                    # Add to candidates
                    candidates.append({
                        'title': title,
                        'price': price,
                        'url': url,
                        'website': 'Flipkart',
                        'image_url': image_url
                    })
                    
                except Exception as e:
                    continue

            # Filter candidates for relevance
            if not candidates:
                return None
                
            # Scoring:
            # 1. Check if all query words are in title (High score)
            # 2. Check if brand (first word) is in title
            # 3. Exclude if "sponsored" text is found (though hard to detect in text only)
            
            query_parts = query.lower().split()
            best_match = None
            max_score = -1
            
            for item in candidates:
                title_lower = item['title'].lower()
                score = 0
                
                # Brand match (First word of query usually)
                if len(query_parts) > 0 and query_parts[0] in title_lower:
                    score += 50  # Massive boost for brand match
                
                # Word overlap score
                for word in query_parts:
                    if word in title_lower:
                        score += 5
                
                # Penalty for very short titles (ads?) or very mismatching ones
                if score > max_score:
                    max_score = score
                    best_match = item
            
            if best_match:
                return best_match
            
            return candidates[0] if candidates else None
        except Exception as e:
            print(f"Flipkart scraper error: {e}")
        
        return None
