import re
import urllib.parse

from bs4 import BeautifulSoup

from core.services.browser import fetch_rendered_html

from .base import BaseScraper


class AmazonScraper(BaseScraper):
    """Scraper for Amazon.in."""

    website = 'Amazon'

    def search(self, query):
        search_url = "https://www.amazon.in/s"
        params = {'k': query}
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
                    diagnostic_message='Amazon blocked the search request before organic results were available.',
                    http_status=http_status,
                )
            elif http_status == 503:
                return self.build_attempt(
                    website=self.website,
                    state='unavailable',
                    diagnostic_message='Amazon search was temporarily unavailable.',
                    http_status=http_status,
                )
            else:
                return self.build_attempt(
                    website=self.website,
                    state='error',
                    diagnostic_message='Amazon could not be rendered for this query.',
                    http_status=http_status,
                )

        candidates = self.parse_candidates(html)
        if not candidates:
            if self.looks_blocked(html):
                return self.build_attempt(
                    website=self.website,
                    state='blocked',
                    diagnostic_message='Amazon returned bot-protection content instead of organic results.',
                    http_status=http_status,
                )
            return self.build_attempt(
                website=self.website,
                state='not_found',
                diagnostic_message='Amazon returned no organic product candidates for this query.',
                http_status=http_status,
            )

        return self.build_attempt(
            website=self.website,
            state='matched',
            candidates=candidates,
            diagnostic_message=f'Parsed {len(candidates)} organic Amazon candidates.',
            http_status=http_status,
        )

    def parse_candidates(self, html):
        soup = BeautifulSoup(html or '', 'html.parser')
        results = []

        for rank, product in enumerate(
            soup.find_all('div', {'data-component-type': 's-search-result'}),
            start=1,
        ):
            if rank > 24:
                break

            title_elem = product.select_one('h2 span')
            title = self.clean_text(title_elem.get_text(" ", strip=True) if title_elem else '')
            if not title:
                continue

            link = product.find('a', href=re.compile(r'/dp/|/gp/'))
            href = link.get('href', '') if link else ''
            url = self._canonicalize_url(href)
            if not url:
                continue

            price = None
            offscreen = product.select_one('span.a-price span.a-offscreen')
            if offscreen:
                price = self.parse_price(offscreen.get_text(strip=True))

            if not price:
                whole = product.select_one('span.a-price-whole')
                fraction = product.select_one('span.a-price-fraction')
                if whole:
                    price = self.parse_price(
                        f"{whole.get_text(strip=True)}.{fraction.get_text(strip=True) if fraction else '00'}"
                    )

            if not price:
                continue

            sponsored = bool(product.find(string=re.compile(r'sponsored', re.I)))
            image = product.select_one('img.s-image')
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
            href = f'https://www.amazon.in{href}'
        if not href.startswith('http'):
            return None
        href = href.split('?', 1)[0]
        href = href.split('/ref=', 1)[0]
        return href
