from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional

import requests
import time


@dataclass
class Candidate:
    title: str
    price: float
    url: str
    image_url: Optional[str] = None
    rank: int = 0
    is_sponsored: bool = False
    raw_text: str = ''


@dataclass
class ScrapeAttempt:
    website: str
    state: str
    candidates: List[Candidate] = field(default_factory=list)
    diagnostic_message: str = ''
    http_status: Optional[int] = None


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
        Search for a product and return a structured scrape attempt.
        
        Returns:
            ScrapeAttempt
        """
        pass
    
    def get_page(self, url, params=None, retries=2):
        """Fetch a webpage with retry logic and return the final response when possible."""
        import time
        import random
        
        last_response = None
        for attempt in range(retries + 1):
            try:
                # Add random delay to avoid rate limiting (1-3 seconds)
                if attempt > 0:
                    delay = random.uniform(2, 4)
                    time.sleep(delay)
                else:
                    time.sleep(random.uniform(1, 2))
                
                response = self.session.get(url, params=params, timeout=20, allow_redirects=True)
                last_response = response
                
                if response.status_code in (429, 502, 503) and attempt < retries:
                    print(f"{response.status_code} for {url} - Attempt {attempt + 1}/{retries + 1}")
                    continue
                    
                return response
            except requests.exceptions.Timeout:
                print(f"Timeout fetching {url} - Attempt {attempt + 1}/{retries + 1}")
                if attempt < retries:
                    continue
                return None
            except requests.RequestException as e:
                print(f"Error fetching {url}: {e} - Attempt {attempt + 1}/{retries + 1}")
                if attempt < retries:
                    continue
                return last_response
        
        return last_response
    
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

    def clean_text(self, text):
        return ' '.join((text or '').split())

    def build_candidate(self, *, title, price, url, image_url=None, rank=0, is_sponsored=False, raw_text=''):
        if not title or not url or price in (None, '', 0):
            return None

        try:
            price_value = float(price)
        except (TypeError, ValueError):
            return None

        if price_value <= 0:
            return None

        return Candidate(
            title=self.clean_text(title),
            price=price_value,
            url=url.strip(),
            image_url=image_url,
            rank=rank,
            is_sponsored=is_sponsored,
            raw_text=self.clean_text(raw_text),
        )

    def build_attempt(self, *, website, state, candidates=None, diagnostic_message='', http_status=None):
        return ScrapeAttempt(
            website=website,
            state=state,
            candidates=candidates or [],
            diagnostic_message=diagnostic_message,
            http_status=http_status,
        )

    def looks_blocked(self, text, url=''):
        sample = f"{url} {(text or '')[:1200]}".lower()
        blocked_markers = [
            'captcha',
            'robot check',
            'automated access',
            'access denied',
            'unusual traffic',
            'temporarily unavailable',
            'request blocked',
        ]
        return any(marker in sample for marker in blocked_markers)

    def is_thin_html(self, text):
        return len((text or '').strip()) < 1200
