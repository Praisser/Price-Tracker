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

    def test_generic_query_allows_minor_typo_and_plural_difference(self):
        decision = evaluate_scrape_candidates(
            'hijab magentic pin',
            [
                Candidate(
                    title='Hijab Magnetic Pins for Women Multi-Use Pinless Scarf Clip',
                    price=139,
                    url='https://example.com/hijab-pins',
                    rank=1,
                ),
                Candidate(
                    title='Round Hijab Magnetic Pins for Women Girls Multi-Use Pinless Magnet Pins',
                    price=149,
                    url='https://example.com/hijab-pins-2',
                    rank=2,
                )
            ],
        )

        self.assertEqual(decision.state, 'matched')
        self.assertEqual(
            decision.accepted_candidate.title,
            'Hijab Magnetic Pins for Women Multi-Use Pinless Scarf Clip'
        )

    def test_generic_brand_laptop_query_accepts_notebook_alias(self):
        decision = evaluate_scrape_candidates(
            'Dell laptop',
            [
                Candidate(
                    title='Dell Inspiron 15 Notebook Intel Core i5 16GB RAM 512GB SSD',
                    price=58999,
                    url='https://example.com/dell-notebook',
                    rank=1,
                ),
                Candidate(
                    title='HP Pavilion 15 Laptop Intel Core i5 16GB RAM 512GB SSD',
                    price=60999,
                    url='https://example.com/hp-laptop',
                    rank=2,
                ),
            ],
        )

        self.assertEqual(decision.state, 'matched')
        self.assertEqual(
            decision.accepted_candidate.title,
            'Dell Inspiron 15 Notebook Intel Core i5 16GB RAM 512GB SSD'
        )

    def test_generic_brand_laptop_query_chooses_best_variant_instead_of_ambiguous(self):
        decision = evaluate_scrape_candidates(
            'Dell laptop',
            [
                Candidate(
                    title='Dell Inspiron 15 Laptop Intel Core i5 16GB RAM 512GB SSD',
                    price=58999,
                    url='https://example.com/dell1',
                    rank=1,
                ),
                Candidate(
                    title='Dell Vostro 14 Laptop Intel Core i7 16GB RAM 1TB SSD',
                    price=67999,
                    url='https://example.com/dell2',
                    rank=2,
                ),
                Candidate(
                    title='Dell Laptop Sleeve 15 inch',
                    price=999,
                    url='https://example.com/sleeve',
                    rank=3,
                ),
            ],
        )

        self.assertEqual(decision.state, 'matched')
        self.assertEqual(
            decision.accepted_candidate.title,
            'Dell Inspiron 15 Laptop Intel Core i5 16GB RAM 512GB SSD'
        )

    def test_monitor_arm_is_rejected_as_accessory(self):
        decision = evaluate_scrape_candidates(
            'Dell monitor',
            [
                Candidate(
                    title='Dell 27 inch QHD Monitor',
                    price=22999,
                    url='https://example.com/monitor',
                    rank=1,
                ),
                Candidate(
                    title='Dell Monitor Arm',
                    price=2999,
                    url='https://example.com/arm',
                    rank=2,
                ),
            ],
        )

        self.assertEqual(decision.state, 'matched')
        self.assertEqual(decision.accepted_candidate.title, 'Dell 27 inch QHD Monitor')

    def test_fridge_alias_matches_refrigerator_listing(self):
        decision = evaluate_scrape_candidates(
            'LG fridge',
            [
                Candidate(
                    title='LG 185 L Direct Cool Single Door Refrigerator with Smart Inverter Compressor',
                    price=16690,
                    url='https://example.com/lg-fridge',
                    rank=1,
                ),
                Candidate(
                    title='LG Refrigerator Stand',
                    price=1499,
                    url='https://example.com/lg-stand',
                    rank=2,
                ),
            ],
        )

        self.assertEqual(decision.state, 'matched')
        self.assertEqual(
            decision.accepted_candidate.title,
            'LG 185 L Direct Cool Single Door Refrigerator with Smart Inverter Compressor'
        )

    def test_generic_washing_machine_query_selects_best_machine(self):
        decision = evaluate_scrape_candidates(
            'washing machine',
            [
                Candidate(
                    title='LG 7 Kg 5 Star Top Loading Washing Machine',
                    price=10990,
                    url='https://example.com/lg-wm',
                    rank=1,
                ),
                Candidate(
                    title='Voltas 6.5 Kg Semi Automatic Washing Machine',
                    price=7990,
                    url='https://example.com/voltas-wm',
                    rank=2,
                ),
                Candidate(
                    title='Washing Machine Cover',
                    price=499,
                    url='https://example.com/cover',
                    rank=3,
                ),
            ],
        )

        self.assertEqual(decision.state, 'matched')
        self.assertEqual(decision.accepted_candidate.title, 'LG 7 Kg 5 Star Top Loading Washing Machine')

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
