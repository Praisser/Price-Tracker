from abc import ABC, abstractmethod
import requests
from bs4 import BeautifulSoup
import time


class BaseScraper(ABC):
    """Base class for all web scrapers."""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
    
    @abstractmethod
    def search(self, query):
        """
        Search for a product and return price data.
        
        Returns:
            dict: {
                'website': str,
                'price': float,
                'url': str,
                'title': str (optional)
            } or None if not found
        """
        pass
    
    def get_page(self, url, params=None, retries=2):
        """Fetch a webpage with error handling and retry logic."""
        import time
        import random
        
        for attempt in range(retries + 1):
            try:
                # Add random delay to avoid rate limiting (1-3 seconds)
                if attempt > 0:
                    delay = random.uniform(2, 4)
                    time.sleep(delay)
                else:
                    time.sleep(random.uniform(1, 2))
                
                response = self.session.get(url, params=params, timeout=20, allow_redirects=True)
                
                # Check status code
                if response.status_code == 503:
                    print(f"503 Service Unavailable for {url} - Attempt {attempt + 1}/{retries + 1}")
                    if attempt < retries:
                        continue
                    return None
                
                response.raise_for_status()
                
                # Check if we got blocked or redirected to a captcha page
                if 'captcha' in response.url.lower() or 'robot' in response.text.lower()[:500]:
                    print(f"Possible bot detection at {url}")
                    return None
                
                # Check if response is valid HTML
                if len(response.content) < 1000:  # Too small, might be an error page
                    print(f"Response too small from {url}")
                    if attempt < retries:
                        continue
                    return None
                    
                return response
            except requests.exceptions.Timeout:
                print(f"Timeout fetching {url} - Attempt {attempt + 1}/{retries + 1}")
                if attempt < retries:
                    continue
                return None
            except requests.exceptions.HTTPError as e:
                print(f"HTTP Error fetching {url}: {e} - Attempt {attempt + 1}/{retries + 1}")
                if attempt < retries and e.response.status_code in [429, 503, 502]:
                    continue
                return None
            except requests.RequestException as e:
                print(f"Error fetching {url}: {e} - Attempt {attempt + 1}/{retries + 1}")
                if attempt < retries:
                    continue
                return None
        
        return None
    
    def parse_price(self, price_str):
        """Extract numeric price from string."""
        if not price_str:
            return None
        
        # Remove currency symbols and commas
        price_str = price_str.replace(',', '').replace('₹', '').replace('$', '').replace('€', '').replace('£', '')
        
        # Extract numbers
        import re
        numbers = re.findall(r'\d+\.?\d*', price_str)
        if numbers:
            try:
                return float(numbers[0])
            except ValueError:
                return None
        return None
