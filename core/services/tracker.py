import smtplib
import statistics
from decimal import Decimal

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from core.constants import WEBSITE_ORDER
from core.models import PriceAlert, PriceHistory, PriceResult, SourceStatus
from core.services.matcher import MatchDecision, evaluate_scrape_candidates
from core.services.scraper.ajio import AjioScraper
from core.services.scraper.amazon import AmazonScraper
from core.services.scraper.base import ScrapeAttempt
from core.services.scraper.flipkart import FlipkartScraper
from core.services.scraper.meesho import MeeshoScraper
from core.services.scraper.myntra import MyntraScraper


SCRAPER_CLASSES = [
    AmazonScraper,
    FlipkartScraper,
    MyntraScraper,
    AjioScraper,
    MeeshoScraper,
]


MIN_PRICE_MAP = {
    'macbook': 40000,
    'laptop': 15000,
    'iphone': 30000,
    'ipad': 20000,
    'samsung galaxy s': 30000,
}


def _format_mail_error(error):
    """Convert low-level SMTP exceptions into user-friendly text."""
    if isinstance(error, smtplib.SMTPAuthenticationError):
        return 'SMTP login failed. Check EMAIL_HOST_USER and use a valid Gmail App Password.'
    return str(error)


def _safe_decimal(value):
    return Decimal(str(value)).quantize(Decimal('0.01'))


def _minimum_safe_price(query):
    query_lower = (query or '').lower()
    for key, limit in MIN_PRICE_MAP.items():
        if key in query_lower:
            return limit
    return 0


def _ordered(items):
    order_map = {website: index for index, website in enumerate(WEBSITE_ORDER)}
    return sorted(items, key=lambda item: order_map.get(item['website'], 999))


def _error_attempt(website, error):
    return ScrapeAttempt(
        website=website,
        state='error',
        diagnostic_message=str(error),
        http_status=None,
    )


def _apply_price_sanity(source_records, *, min_safe_price):
    matched_records = [
        record for record in source_records
        if record['state'] == SourceStatus.State.MATCHED and record['accepted_candidate']
    ]

    if not matched_records:
        return source_records

    prices = [record['accepted_candidate'].price for record in matched_records]
    median_price = statistics.median(prices) if len(prices) >= 2 else None
    price_floor = max(min_safe_price, median_price * 0.2) if median_price is not None else min_safe_price
    price_ceiling = median_price * 5.0 if median_price is not None else None

    for record in matched_records:
        price = record['accepted_candidate'].price
        if price < min_safe_price:
            record['state'] = SourceStatus.State.AMBIGUOUS
            record['diagnostic_message'] = (
                f'Rejected as unsafe because the parsed price ₹{price:.2f} fell below the category floor of ₹{min_safe_price}.'
            )
            record['accepted_candidate'] = None
            continue

        if price_floor and price < price_floor:
            record['state'] = SourceStatus.State.AMBIGUOUS
            record['diagnostic_message'] = (
                f'Rejected as a cross-source outlier because ₹{price:.2f} was far below the median live price.'
            )
            record['accepted_candidate'] = None
            continue

        if price_ceiling and price > price_ceiling:
            record['state'] = SourceStatus.State.AMBIGUOUS
            record['diagnostic_message'] = (
                f'Rejected as a cross-source outlier because ₹{price:.2f} was far above the median live price.'
            )
            record['accepted_candidate'] = None

    return source_records


def _decision_from_attempt(query, attempt):
    if attempt.state != 'matched' or not attempt.candidates:
        return MatchDecision(
            state=attempt.state,
            diagnostic_message=attempt.diagnostic_message,
            candidate_count=len(attempt.candidates),
        )
    return evaluate_scrape_candidates(query, attempt.candidates)


def track_prices_for_product(product):
    """
    Evaluate all configured sources, persist their last-known states,
    save only confident accepted prices, and trigger alerts for accepted matches.
    """
    query = product.search_query
    min_safe_price = _minimum_safe_price(query)
    source_records = []

    print(f"\n=== Tracking prices for: {product.name} ===")

    for scraper_class in SCRAPER_CLASSES:
        scraper = scraper_class()
        website = getattr(scraper, 'website', scraper.__class__.__name__.replace('Scraper', ''))

        try:
            attempt = scraper.search(query)
        except Exception as error:
            print(f"[X] {website} - Error: {error}")
            attempt = _error_attempt(website, error)

        decision = _decision_from_attempt(query, attempt)
        accepted_candidate = decision.accepted_candidate if decision.state == 'matched' else None
        diagnostic_message = decision.diagnostic_message or attempt.diagnostic_message

        if decision.state == 'matched' and accepted_candidate:
            print(f"[MATCH] {website} -> {accepted_candidate.title} @ ₹{accepted_candidate.price}")
        else:
            print(f"[{decision.state.upper()}] {website} - {diagnostic_message}")

        source_records.append({
            'website': website,
            'state': decision.state,
            'diagnostic_message': diagnostic_message,
            'http_status': attempt.http_status,
            'accepted_candidate': accepted_candidate,
            'matched_title': decision.matched_title or (accepted_candidate.title if accepted_candidate else ''),
            'match_confidence': decision.confidence,
        })

    source_records = _apply_price_sanity(source_records, min_safe_price=min_safe_price)

    accepted_results = []
    now = timezone.now()

    with transaction.atomic():
        for record in source_records:
            website = record['website']
            accepted_candidate = record['accepted_candidate']

            SourceStatus.objects.update_or_create(
                product=product,
                website=website,
                defaults={
                    'state': record['state'],
                    'checked_at': now,
                    'diagnostic_message': record['diagnostic_message'],
                    'matched_title': record['matched_title'],
                    'match_confidence': record['match_confidence'],
                    'http_status': record['http_status'],
                },
            )

            if record['state'] == SourceStatus.State.MATCHED and accepted_candidate:
                price_result, _created = PriceResult.objects.get_or_create(
                    product=product,
                    website=website,
                    defaults={
                        'title': accepted_candidate.title,
                        'price': _safe_decimal(accepted_candidate.price),
                        'url': accepted_candidate.url,
                        'image_url': accepted_candidate.image_url,
                        'match_confidence': record['match_confidence'],
                        'scraped_at': now,
                    },
                )
                price_result.title = accepted_candidate.title
                price_result.price = _safe_decimal(accepted_candidate.price)
                price_result.url = accepted_candidate.url
                price_result.image_url = accepted_candidate.image_url
                price_result.match_confidence = record['match_confidence']
                price_result.scraped_at = now
                price_result.save()

                PriceHistory.objects.create(
                    product=product,
                    website=website,
                    price=price_result.price,
                )

                accepted_results.append({
                    'website': website,
                    'title': accepted_candidate.title,
                    'price': float(price_result.price),
                    'url': accepted_candidate.url,
                    'image_url': accepted_candidate.image_url,
                    'match_confidence': record['match_confidence'],
                })

                check_alerts(product, price_result.price, accepted_candidate.url)
            else:
                PriceResult.objects.filter(product=product, website=website).delete()

    source_statuses = [
        {
            'website': record['website'],
            'state': record['state'],
            'diagnostic_message': record['diagnostic_message'],
            'matched_title': record['matched_title'],
            'match_confidence': record['match_confidence'],
            'http_status': record['http_status'],
        }
        for record in source_records
    ]

    return {
        'accepted_results': _ordered(accepted_results),
        'source_statuses': _ordered(source_statuses),
    }


def check_alerts(product, current_price, url):
    """
    Check if current price triggers any active alerts for the product.
    Sends email if threshold is met.
    """
    alerts = PriceAlert.objects.filter(product=product, is_active=True, target_price__gte=current_price)
    result = {
        'matched': alerts.count(),
        'sent': 0,
        'failed': 0,
        'errors': [],
    }

    for alert in alerts:
        subject = f"Price Alert: {product.name} is now ₹{current_price}!"
        message = f"""
        Good news!

        The price for "{product.name}" has dropped to ₹{current_price}, which is below your target of ₹{alert.target_price}.

        Grab it here: {url}

        Cheers,
        Price Tracker
        """

        try:
            send_mail(
                subject,
                message,
                settings.EMAIL_HOST_USER,
                [alert.email],
                fail_silently=False,
            )
            print(f"Email sent to {alert.email}")
            result['sent'] += 1

            alert.is_active = False
            alert.save()
        except Exception as error:
            print(f"Failed to send email to {alert.email}: {error}")
            result['failed'] += 1
            result['errors'].append({
                'email': alert.email,
                'message': _format_mail_error(error)
            })

    return result
