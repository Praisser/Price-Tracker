from django.test import SimpleTestCase

from core.services.matcher import build_query_profile, evaluate_scrape_candidates
from core.services.scraper.base import Candidate


class MatcherTests(SimpleTestCase):
    def test_query_profile_extracts_hard_and_soft_variants(self):
        profile = build_query_profile('MacBook Air M3 16GB 512GB Silver')

        self.assertIn('macbook', profile.core_tokens)
        self.assertIn('air', profile.major_variant_tokens)
        self.assertIn('m3', profile.technical_variant_tokens)
        self.assertIn('16gb', profile.technical_variant_tokens)
        self.assertIn('512gb', profile.technical_variant_tokens)
        self.assertIn('silver', profile.soft_variant_tokens)
        self.assertNotIn('silver', profile.core_tokens)

    def test_accessory_candidate_is_rejected(self):
        decision = evaluate_scrape_candidates(
            'iPhone 17',
            [
                Candidate(
                    title='iPhone 17 Silicone Case with MagSafe',
                    price=1499,
                    url='https://example.com/case',
                    rank=1,
                )
            ],
        )

        self.assertEqual(decision.state, 'not_found')

    def test_mobile_accessories_candidate_is_rejected(self):
        decision = evaluate_scrape_candidates(
            'iPhone 17 Pro Max',
            [
                Candidate(
                    title='Luxury Kase iPhone 17 Pro Max Fashion Mobile Accessories',
                    price=799,
                    url='https://example.com/accessory',
                    rank=1,
                )
            ],
        )

        self.assertEqual(decision.state, 'not_found')

    def test_wrong_storage_variant_becomes_ambiguous(self):
        decision = evaluate_scrape_candidates(
            'iPhone 17 256GB',
            [
                Candidate(
                    title='Apple iPhone 17 128GB Blue',
                    price=79999,
                    url='https://example.com/iphone-128',
                    rank=1,
                )
            ],
        )

        self.assertEqual(decision.state, 'ambiguous')

    def test_conflicting_variants_become_ambiguous(self):
        decision = evaluate_scrape_candidates(
            'iPhone 17',
            [
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
        )

        self.assertEqual(decision.state, 'ambiguous')

    def test_exact_variant_is_selected(self):
        decision = evaluate_scrape_candidates(
            'Samsung Galaxy S26 Ultra 256GB',
            [
                Candidate(
                    title='Samsung Galaxy S26 Ultra 256GB Titanium',
                    price=106999,
                    url='https://example.com/s26-ultra',
                    rank=1,
                ),
                Candidate(
                    title='Samsung Galaxy S26 Ultra Case',
                    price=999,
                    url='https://example.com/s26-case',
                    rank=2,
                ),
            ],
        )

        self.assertEqual(decision.state, 'matched')
        self.assertEqual(decision.accepted_candidate.title, 'Samsung Galaxy S26 Ultra 256GB Titanium')

    def test_refurbished_candidate_is_rejected_unless_requested(self):
        decision = evaluate_scrape_candidates(
            'iPhone 17 256GB',
            [
                Candidate(
                    title='Apple iPhone 17 Renewed 256GB Blue',
                    price=69999,
                    url='https://example.com/renewed',
                    rank=1,
                )
            ],
        )
        self.assertEqual(decision.state, 'not_found')

        decision = evaluate_scrape_candidates(
            'iPhone 17 renewed 256GB',
            [
                Candidate(
                    title='Apple iPhone 17 Renewed 256GB Blue',
                    price=69999,
                    url='https://example.com/renewed',
                    rank=1,
                )
            ],
        )
        self.assertEqual(decision.state, 'matched')
