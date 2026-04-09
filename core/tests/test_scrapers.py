from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from core.services.scraper.ajio import AjioScraper
from core.services.scraper.amazon import AmazonScraper
from core.services.scraper.flipkart import FlipkartScraper
from core.services.scraper.meesho import MeeshoScraper
from core.services.scraper.myntra import MyntraScraper


FIXTURE_DIR = Path(__file__).resolve().parent / 'fixtures'


def load_fixture(name):
    return (FIXTURE_DIR / name).read_text()


class ScraperParserTests(SimpleTestCase):
    def test_amazon_parser_extracts_multiple_candidates(self):
        candidates = AmazonScraper().parse_candidates(load_fixture('amazon_search.html'))

        self.assertEqual(len(candidates), 2)
        self.assertEqual(candidates[0].title, 'Apple iPhone 17 256GB Blue')
        self.assertEqual(candidates[0].url, 'https://www.amazon.in/Apple-iPhone-17-Blue-256GB/dp/B0AMZ1')
        self.assertTrue(candidates[1].is_sponsored)

    def test_flipkart_parser_extracts_candidates_and_canonicalizes_urls(self):
        candidates = FlipkartScraper().parse_candidates(load_fixture('flipkart_search.html'))

        self.assertEqual(len(candidates), 2)
        self.assertEqual(candidates[0].title, 'Apple iPhone 17 (Blue, 256 GB)')
        self.assertEqual(candidates[0].url, 'https://www.flipkart.com/apple-iphone-17-blue-256-gb/p/itm123456')
        self.assertTrue(candidates[1].is_sponsored)

    def test_myntra_parser_reads_public_page_payload(self):
        candidates = MyntraScraper().parse_candidates(load_fixture('myntra_search.html'))

        self.assertEqual(len(candidates), 2)
        self.assertEqual(candidates[0].title, 'Nike Air Zoom Pegasus 41')
        self.assertEqual(candidates[0].url, 'https://www.myntra.com/nike-air-zoom-pegasus-41/12345/buy')

    @patch('core.services.scraper.ajio.fetch_rendered_html', return_value=None)
    def test_ajio_reports_unavailable_when_public_search_is_blocked(self, _mock_render):
        scraper = AjioScraper()
        scraper.get_page = lambda *args, **kwargs: SimpleNamespace(
            status_code=403,
            text='Access denied by edge security policy',
            url='https://www.ajio.com/search/?text=iphone+17',
        )

        attempt = scraper.search('iphone 17')

        self.assertEqual(attempt.state, 'unavailable')

    @patch('core.services.scraper.meesho.fetch_rendered_html', return_value=None)
    def test_meesho_reports_unavailable_when_public_search_is_blocked(self, _mock_render):
        scraper = MeeshoScraper()
        scraper.get_page = lambda *args, **kwargs: SimpleNamespace(
            status_code=403,
            text='Access denied',
            url='https://www.meesho.com/search?q=iphone+17',
        )

        attempt = scraper.search('iphone 17')

        self.assertEqual(attempt.state, 'unavailable')
