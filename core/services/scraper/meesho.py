import json
import urllib.parse

from bs4 import BeautifulSoup

from core.services.browser import fetch_rendered_html

from .base import BaseScraper


class MeeshoScraper(BaseScraper):
    """Best-effort scraper for Meesho public search pages."""

    website = 'Meesho'

    def search(self, query):
        url = f"https://www.meesho.com/search?q={urllib.parse.quote_plus(query)}"
        response = self.get_page(url)
        html = response.text if response else ''
        http_status = response.status_code if response else None

        rendered = fetch_rendered_html(url) if (not html or http_status in (403, 429, 503) or self.looks_blocked(html, response.url if response else url)) else None
        if rendered and rendered.html:
            html = rendered.html
            http_status = rendered.status or http_status

        if not html or http_status in (403, 429) or self.looks_blocked(html):
            return self.build_attempt(
                website=self.website,
                state='unavailable',
                diagnostic_message='Meesho did not expose a trustworthy public search page for this query.',
                http_status=http_status,
            )

        candidates = self.parse_candidates(html)
        if not candidates:
            return self.build_attempt(
                website=self.website,
                state='not_found',
                diagnostic_message='Meesho returned no public product candidates for this query.',
                http_status=http_status,
            )

        return self.build_attempt(
            website=self.website,
            state='matched',
            candidates=candidates,
            diagnostic_message=f'Parsed {len(candidates)} Meesho candidates from public page data.',
            http_status=http_status,
        )

    def parse_candidates(self, html):
        soup = BeautifulSoup(html or '', 'html.parser')
        script = soup.find('script', id='__NEXT_DATA__')
        if not script or not script.string:
            return []

        try:
            payload = json.loads(script.string)
        except json.JSONDecodeError:
            return []

        products = []
        self._collect_product_dicts(payload, products)
        results = []
        seen_urls = set()

        for rank, product in enumerate(products, start=1):
            if rank > 40:
                break

            slug = product.get('slug') or product.get('product_slug')
            url = f'https://www.meesho.com/{slug}/p/{product.get("id") or product.get("catalog_id") or ""}'.rstrip('/')
            if not slug or url in seen_urls:
                continue
            seen_urls.add(url)

            price = (
                product.get('price')
                or product.get('discounted_price')
                or product.get('sale_price')
                or product.get('discountedPrice')
            )
            image_url = product.get('image') or product.get('image_url') or product.get('imageUrl')
            candidate = self.build_candidate(
                title=product.get('name') or product.get('title'),
                price=price,
                url=url,
                image_url=image_url,
                rank=rank,
                raw_text=json.dumps(product, ensure_ascii=True),
            )
            if candidate:
                results.append(candidate)

        return results

    def _collect_product_dicts(self, node, products):
        if isinstance(node, dict):
            keys = set(node.keys())
            if {'name', 'slug'} <= keys and ({'price'} & keys or {'discounted_price', 'sale_price', 'discountedPrice'} & keys):
                products.append(node)
            for value in node.values():
                self._collect_product_dicts(value, products)
        elif isinstance(node, list):
            for value in node:
                self._collect_product_dicts(value, products)
