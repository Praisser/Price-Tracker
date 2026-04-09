import re
import urllib.parse

from bs4 import BeautifulSoup

from core.services.browser import fetch_rendered_html

from .base import BaseScraper


class FlipkartScraper(BaseScraper):
    """Scraper for Flipkart."""

    website = 'Flipkart'

    def search(self, query):
        search_url = "https://www.flipkart.com/search"
        params = {'q': query}
        response = self.get_page(search_url, params=params)
        html = response.text if response else ''
        http_status = response.status_code if response else None

        use_playwright = (
            not html
            or http_status in (403, 429, 503)
            or self.looks_blocked(html, response.url if response else search_url)
            or self.is_thin_html(html)
        )

        if use_playwright:
            url = f"{search_url}?{urllib.parse.urlencode(params)}"
            rendered = fetch_rendered_html(url)
            if rendered and rendered.html:
                html = rendered.html
                http_status = rendered.status or http_status
            elif http_status in (403, 429):
                return self.build_attempt(
                    website=self.website,
                    state='blocked',
                    diagnostic_message='Flipkart blocked the search request before results could be parsed.',
                    http_status=http_status,
                )
            elif http_status == 503:
                return self.build_attempt(
                    website=self.website,
                    state='unavailable',
                    diagnostic_message='Flipkart search was temporarily unavailable.',
                    http_status=http_status,
                )
            else:
                return self.build_attempt(
                    website=self.website,
                    state='error',
                    diagnostic_message='Flipkart could not be rendered for this query.',
                    http_status=http_status,
                )

        candidates = self.parse_candidates(html)
        if not candidates:
            if self.looks_blocked(html):
                return self.build_attempt(
                    website=self.website,
                    state='blocked',
                    diagnostic_message='Flipkart returned a blocked or bot-detection page.',
                    http_status=http_status,
                )
            return self.build_attempt(
                website=self.website,
                state='not_found',
                diagnostic_message='Flipkart returned no organic product candidates for this query.',
                http_status=http_status,
            )

        return self.build_attempt(
            website=self.website,
            state='matched',
            candidates=candidates,
            diagnostic_message=f'Parsed {len(candidates)} Flipkart candidates.',
            http_status=http_status,
        )

    def parse_candidates(self, html):
        soup = BeautifulSoup(html or '', 'html.parser')
        results = []
        seen_urls = set()

        product_blocks = soup.find_all('div', {'data-id': True})
        if not product_blocks:
            product_blocks = [link.find_parent('div') for link in soup.find_all('a', href=re.compile(r'/p/'))]

        for rank, product in enumerate([block for block in product_blocks if block], start=1):
            if rank > 40:
                break

            title_elem = product.find('div', class_=re.compile(r'_4rR01T|s1Q9rs|IRpwTa'))
            title = self.clean_text(title_elem.get_text(" ", strip=True) if title_elem else '')
            if not title:
                image = product.find('img', alt=True)
                title = self.clean_text(image.get('alt', '') if image else '')
            if not title:
                continue

            price_elem = product.find('div', class_=re.compile(r'_30jeq3'))
            price = self.parse_price(price_elem.get_text(strip=True)) if price_elem else None
            if not price:
                price_match = re.search(r'₹\s*([\d,]+)', product.get_text(" ", strip=True))
                price = self.parse_price(price_match.group(0)) if price_match else None
            if not price:
                continue

            link = product.find('a', href=re.compile(r'/p/'))
            href = link.get('href', '') if link else ''
            url = self._canonicalize_url(href)
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)

            sponsored = bool(re.search(r'sponsored', product.get_text(" ", strip=True), re.I))
            image = product.find('img', src=True)
            candidate = self.build_candidate(
                title=title,
                price=price,
                url=url,
                image_url=image.get('src') if image else None,
                rank=rank,
                is_sponsored=sponsored,
                raw_text=product.get_text(" ", strip=True),
            )
            if candidate:
                results.append(candidate)

        return results

    def _canonicalize_url(self, href):
        if not href:
            return None
        if href.startswith('/'):
            href = f'https://www.flipkart.com{href}'
        if not href.startswith('http'):
            return None
        return href.split('?', 1)[0]
