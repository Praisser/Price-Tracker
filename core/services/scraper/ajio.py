import re
import urllib.parse

from bs4 import BeautifulSoup

from core.services.browser import fetch_rendered_html

from .base import BaseScraper


class AjioScraper(BaseScraper):
    """Best-effort scraper for Ajio public search results."""

    website = 'Ajio'

    def search(self, query):
        search_url = "https://www.ajio.com/search/"
        params = {'text': query}
        response = self.get_page(search_url, params=params)
        html = response.text if response else ''
        http_status = response.status_code if response else None

        rendered_html = None
        rendered_status = None
        if not html or http_status in (403, 429, 503) or self.looks_blocked(html, response.url if response else search_url):
            rendered = fetch_rendered_html(f"{search_url}?{urllib.parse.urlencode(params)}")
            if rendered and rendered.html:
                rendered_html = rendered.html
                rendered_status = rendered.status

        html = rendered_html or html
        http_status = rendered_status or http_status

        if not html:
            return self.build_attempt(
                website=self.website,
                state='unavailable',
                diagnostic_message='Ajio could not be reached through its public search surface.',
                http_status=http_status,
            )

        if http_status in (403, 429) or self.looks_blocked(html):
            return self.build_attempt(
                website=self.website,
                state='unavailable',
                diagnostic_message='Ajio blocked the public search page, so no trustworthy result could be collected.',
                http_status=http_status,
            )

        candidates = self.parse_candidates(html)
        if not candidates:
            return self.build_attempt(
                website=self.website,
                state='not_found',
                diagnostic_message='Ajio did not expose any organic public candidates for this query.',
                http_status=http_status,
            )

        return self.build_attempt(
            website=self.website,
            state='matched',
            candidates=candidates,
            diagnostic_message=f'Parsed {len(candidates)} Ajio candidates from public listings.',
            http_status=http_status,
        )

    def parse_candidates(self, html):
        soup = BeautifulSoup(html or '', 'html.parser')
        results = []

        for rank, product in enumerate(soup.select('div.item, div.rilrtl-products-list__item, div[data-testid="product-card"]'), start=1):
            if rank > 40:
                break

            title_elem = product.select_one('.nameCls, .brand, .contentHolder .name')
            title = self.clean_text(title_elem.get_text(" ", strip=True) if title_elem else '')
            price_elem = product.select_one('.price, .priceCls')
            price = self.parse_price(price_elem.get_text(strip=True)) if price_elem else None
            link = product.find('a', href=True)
            href = link.get('href', '') if link else ''
            if href.startswith('/'):
                href = f'https://www.ajio.com{href}'
            image = product.find('img', src=True)

            candidate = self.build_candidate(
                title=title,
                price=price,
                url=href,
                image_url=image.get('src') if image else None,
                rank=rank,
                raw_text=product.get_text(" ", strip=True),
            )
            if candidate:
                results.append(candidate)

        return results
