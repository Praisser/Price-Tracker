from django.test import TestCase
from django.urls import reverse
from unittest.mock import patch

from core.models import PriceResult, Product, SourceStatus
from core.services.scraper.base import Candidate, ScrapeAttempt
from core.services.tracker import track_prices_for_product


class AmazonExactScraper:
    website = 'Amazon'

    def search(self, query):
        return ScrapeAttempt(
            website=self.website,
            state='matched',
            candidates=[
                Candidate(
                    title='Samsung Galaxy S26 Ultra 256GB Titanium',
                    price=106999,
                    url='https://example.com/amazon-s26',
                    image_url='https://example.com/amazon-s26.jpg',
                    rank=1,
                )
            ],
            diagnostic_message='Parsed Amazon candidates.',
            http_status=200,
        )


class FlipkartExactScraper:
    website = 'Flipkart'

    def search(self, query):
        return ScrapeAttempt(
            website=self.website,
            state='matched',
            candidates=[
                Candidate(
                    title='Samsung Galaxy S26 Ultra 256GB Black',
                    price=105999,
                    url='https://example.com/flipkart-s26',
                    image_url='https://example.com/flipkart-s26.jpg',
                    rank=1,
                )
            ],
            diagnostic_message='Parsed Flipkart candidates.',
            http_status=200,
        )


class MyntraExactScraper:
    website = 'Myntra'

    def search(self, query):
        return ScrapeAttempt(
            website=self.website,
            state='matched',
            candidates=[
                Candidate(
                    title='Samsung Galaxy S26 Ultra 256GB Silver',
                    price=107499,
                    url='https://example.com/myntra-s26',
                    image_url='https://example.com/myntra-s26.jpg',
                    rank=1,
                )
            ],
            diagnostic_message='Parsed Myntra candidates.',
            http_status=200,
        )


class AjioUnavailableScraper:
    website = 'Ajio'

    def search(self, query):
        return ScrapeAttempt(
            website=self.website,
            state='unavailable',
            diagnostic_message='Ajio blocked the public search page.',
            http_status=403,
        )


class MeeshoBlockedScraper:
    website = 'Meesho'

    def search(self, query):
        return ScrapeAttempt(
            website=self.website,
            state='blocked',
            diagnostic_message='Meesho returned bot-protection content.',
            http_status=403,
        )


class AmazonAmbiguousScraper:
    website = 'Amazon'

    def search(self, query):
        return ScrapeAttempt(
            website=self.website,
            state='matched',
            candidates=[
                Candidate(
                    title='Apple iPhone 17 128GB Blue',
                    price=79999,
                    url='https://example.com/iphone-128',
                    rank=1,
                ),
                Candidate(
                    title='Apple iPhone 17 256GB Blue',
                    price=89999,
                    url='https://example.com/iphone-256',
                    rank=2,
                ),
            ],
            diagnostic_message='Parsed Amazon candidates.',
            http_status=200,
        )


class EmptyNotFoundScraper:
    def __init__(self, website):
        self.website = website

    def search(self, query):
        return ScrapeAttempt(
            website=self.website,
            state='not_found',
            diagnostic_message=f'{self.website} had no candidates.',
            http_status=200,
        )


class TrackerIntegrationTests(TestCase):
    @patch(
        'core.services.tracker.SCRAPER_CLASSES',
        new=[AmazonExactScraper, FlipkartExactScraper, MyntraExactScraper, AjioUnavailableScraper, MeeshoBlockedScraper],
    )
    def test_tracker_persists_five_source_statuses_and_only_confident_matches(self):
        product = Product.objects.create(name='Samsung Galaxy S26 Ultra 256GB', search_query='Samsung Galaxy S26 Ultra 256GB')

        result = track_prices_for_product(product)

        self.assertEqual(len(result['accepted_results']), 3)
        self.assertEqual(SourceStatus.objects.filter(product=product).count(), 5)
        self.assertEqual(PriceResult.objects.filter(product=product).count(), 3)
        self.assertEqual(
            SourceStatus.objects.get(product=product, website='Ajio').state,
            SourceStatus.State.UNAVAILABLE,
        )
        self.assertEqual(
            SourceStatus.objects.get(product=product, website='Meesho').state,
            SourceStatus.State.BLOCKED,
        )

    @patch(
        'core.services.tracker.SCRAPER_CLASSES',
        new=[
            AmazonAmbiguousScraper,
            lambda: EmptyNotFoundScraper('Flipkart'),
            lambda: EmptyNotFoundScraper('Myntra'),
            lambda: EmptyNotFoundScraper('Ajio'),
            lambda: EmptyNotFoundScraper('Meesho'),
        ],
    )
    def test_tracker_keeps_statuses_when_no_confident_match_exists(self):
        product = Product.objects.create(name='iPhone 17', search_query='iPhone 17')

        result = track_prices_for_product(product)

        self.assertEqual(result['accepted_results'], [])
        self.assertEqual(SourceStatus.objects.filter(product=product).count(), 5)
        self.assertEqual(PriceResult.objects.filter(product=product).count(), 0)
        self.assertEqual(
            SourceStatus.objects.get(product=product, website='Amazon').state,
            SourceStatus.State.AMBIGUOUS,
        )

    @patch(
        'core.services.tracker.SCRAPER_CLASSES',
        new=[AmazonExactScraper, FlipkartExactScraper, MyntraExactScraper, AjioUnavailableScraper, MeeshoBlockedScraper],
    )
    def test_dashboard_shows_all_five_source_entries(self):
        product = Product.objects.create(name='Samsung Galaxy S26 Ultra 256GB', search_query='Samsung Galaxy S26 Ultra 256GB')
        track_prices_for_product(product)

        response = self.client.get(reverse('dashboard'), {'product_id': product.id})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['source_entries']), 5)
        self.assertEqual(response.context['total_found'], 3)

    @patch(
        'core.services.tracker.SCRAPER_CLASSES',
        new=[AmazonExactScraper, AjioUnavailableScraper, MeeshoBlockedScraper, lambda: EmptyNotFoundScraper('Flipkart'), lambda: EmptyNotFoundScraper('Myntra')],
    )
    def test_price_editor_only_lists_matched_sources(self):
        product = Product.objects.create(name='Samsung Galaxy S26 Ultra 256GB', search_query='Samsung Galaxy S26 Ultra 256GB')
        track_prices_for_product(product)

        response = self.client.get(reverse('price_editor', args=[product.id]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['price_results']), 1)
