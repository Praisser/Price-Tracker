import json
import re
import urllib.parse

from core.services.browser import fetch_rendered_html

from .base import BaseScraper


class MyntraScraper(BaseScraper):
    """Scraper for Myntra."""

    website = 'Myntra'

    def search(self, query):
        url = f"https://www.myntra.com/{urllib.parse.quote_plus(query)}"
        response = self.get_page(url)
        html = response.text if response else ''
        http_status = response.status_code if response else None

        use_playwright = (
            not html
            or http_status in (403, 429, 503)
            or self.looks_blocked(html, response.url if response else url)
            or self.is_thin_html(html)
        )

        if use_playwright:
            rendered = fetch_rendered_html(url)
            if rendered and rendered.html:
                html = rendered.html
                http_status = rendered.status or http_status
            elif http_status in (403, 429):
                return self.build_attempt(
                    website=self.website,
                    state='blocked',
                    diagnostic_message='Myntra blocked the search request before results could be parsed.',
                    http_status=http_status,
                )
            elif http_status == 503:
                return self.build_attempt(
                    website=self.website,
                    state='unavailable',
                    diagnostic_message='Myntra search was temporarily unavailable.',
                    http_status=http_status,
                )
            else:
                return self.build_attempt(
                    website=self.website,
                    state='error',
                    diagnostic_message='Myntra could not be rendered for this query.',
                    http_status=http_status,
                )

        candidates = self.parse_candidates(html)
        if not candidates:
            if self.looks_blocked(html):
                return self.build_attempt(
                    website=self.website,
                    state='blocked',
                    diagnostic_message='Myntra returned blocked or maintenance content.',
                    http_status=http_status,
                )
            return self.build_attempt(
                website=self.website,
                state='not_found',
                diagnostic_message='Myntra returned no listing candidates for this query.',
                http_status=http_status,
            )

        return self.build_attempt(
            website=self.website,
            state='matched',
            candidates=candidates,
            diagnostic_message=f'Parsed {len(candidates)} Myntra candidates from public page data.',
            http_status=http_status,
        )

    def parse_candidates(self, html):
        payload = self._extract_myntra_payload(html or '')
        if not payload:
            return []

        products = payload.get('searchData', {}).get('results', {}).get('products', [])
        results = []
        for rank, product in enumerate(products, start=1):
            if rank > 40:
                break

            price = product.get('discountedPrice') or product.get('price')
            image_url = None
            images = product.get('images') or []
            if images:
                image_url = images[0].get('src') or images[0].get('imageURL')

            candidate = self.build_candidate(
                title=product.get('productName') or product.get('product'),
                price=price,
                url=self._canonicalize_url(product.get('landingPageUrl')),
                image_url=image_url,
                rank=rank,
                raw_text=json.dumps(product, ensure_ascii=True),
            )
            if candidate:
                results.append(candidate)

        return results

    def _extract_myntra_payload(self, html):
        match = re.search(r'window\.__myx\s*=\s*(\{.*?\})\s*;?\s*</script>', html, re.S)
        if not match:
            return None
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            return None

    def _canonicalize_url(self, path):
        if not path:
            return None
        if path.startswith('http'):
            return path
        return f'https://www.myntra.com/{path.lstrip("/")}'
