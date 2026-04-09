import json
from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from core.constants import SOURCE_STATE_LABELS, WEBSITE_ORDER

from .models import PriceAlert, PriceHistory, PriceResult, Product, SourceStatus
from .services.comparator import find_best_price, sort_by_price


def _source_entries_for(product, best_result):
    price_results = {
        result.website: result
        for result in PriceResult.objects.filter(product=product)
    }
    source_statuses = {
        status.website: status
        for status in SourceStatus.objects.filter(product=product)
    }

    entries = []
    for website in WEBSITE_ORDER:
        result = price_results.get(website)
        status = source_statuses.get(website)
        state = status.state if status else (SourceStatus.State.MATCHED if result else SourceStatus.State.UNAVAILABLE)
        confidence = (
            status.match_confidence if status and status.match_confidence is not None
            else result.match_confidence if result and result.match_confidence is not None
            else None
        )
        matched_title = (
            status.matched_title if status and status.matched_title
            else result.title if result and result.title
            else ''
        )
        diagnostic_message = (
            status.diagnostic_message if status and status.diagnostic_message
            else 'Matched from a legacy cached price row.' if result
            else 'No source check has been recorded for this website yet.'
        )

        entries.append({
            'website': website,
            'state': state,
            'state_label': SOURCE_STATE_LABELS.get(state, state.replace('_', ' ').title()),
            'result': result,
            'price': result.price if result else None,
            'url': result.url if result else None,
            'image_url': result.image_url if result else None,
            'match_confidence': confidence,
            'matched_title': matched_title,
            'diagnostic_message': diagnostic_message,
            'http_status': status.http_status if status else None,
            'is_best': bool(result and best_result and result.id == best_result.id),
        })

    return entries


def _warning_for(entries):
    missing = [
        f"{entry['website']} ({entry['state_label']})"
        for entry in entries
        if entry['state'] != SourceStatus.State.MATCHED
    ]
    if not missing:
        return None
    return f'Checked all {len(WEBSITE_ORDER)} sources. No confident result from: {", ".join(missing)}.'


def dashboard(request):
    """Display the main dashboard with search functionality."""
    context = {}
    product_id = request.GET.get('product_id')
    error_param = request.GET.get('error')

    if product_id:
        try:
            product = Product.objects.get(pk=product_id)
            price_results = list(PriceResult.objects.filter(product=product))
            sorted_results = sort_by_price(price_results, ascending=True)
            best_result = find_best_price(sorted_results)
            best_price = best_result.price if best_result else None

            for result in sorted_results:
                result.is_best = bool(best_result and result.id == best_result.id)

            source_entries = _source_entries_for(product, best_result)
            matched_entries = [entry for entry in source_entries if entry['state'] == SourceStatus.State.MATCHED and entry['result']]
            warning = _warning_for(source_entries)

            history_qs = PriceHistory.objects.filter(product=product).order_by('timestamp')
            history_data = {}
            for entry in history_qs:
                history_data.setdefault(entry.website, []).append({
                    'x': entry.timestamp.isoformat(),
                    'y': float(entry.price)
                })

            from django.core.serializers.json import DjangoJSONEncoder
            history_json = json.dumps(history_data, cls=DjangoJSONEncoder)

            context = {
                'product': product,
                'price_results': sorted_results,
                'source_entries': source_entries,
                'best_result': best_result,
                'best_price': best_price,
                'has_results': len(matched_entries) > 0,
                'has_source_entries': bool(source_entries),
                'total_expected': len(WEBSITE_ORDER),
                'total_found': len(matched_entries),
                'total_checked': len(source_entries),
                'history_json': history_json,
                'warning': warning if matched_entries else None,
            }

            if error_param == 'no_results' and not matched_entries:
                context['error'] = (
                    f'No confident prices were accepted for "{product.name}". '
                    'All 5 sources were checked, but none returned a trustworthy exact match.'
                )
        except Product.DoesNotExist:
            context['error'] = 'Product not found'

    return render(request, 'dashboard.html', context)


def search_product(request):
    """Handle product search and trigger scraping."""
    if request.method == 'POST':
        query = request.POST.get('query', '').strip()

        if not query:
            return redirect('dashboard')

        cache_hours = getattr(settings, 'CACHE_EXPIRY_HOURS', 6)
        cache_time = timezone.now() - timedelta(hours=cache_hours)
        product = Product.objects.filter(search_query__iexact=query).first()

        if product:
            recent_statuses = set(
                SourceStatus.objects.filter(
                    product=product,
                    checked_at__gte=cache_time
                ).values_list('website', flat=True)
            )
            if len(recent_statuses) == len(WEBSITE_ORDER):
                return redirect(f'/?product_id={product.id}')

        if not product:
            product = Product.objects.create(
                name=query,
                search_query=query
            )

        from .services.tracker import track_prices_for_product

        tracking_result = track_prices_for_product(product)
        scraped_results = tracking_result['accepted_results']

        if not scraped_results:
            print("No confident results accepted from any scraper")
            return redirect(f'/?product_id={product.id}&error=no_results')

        print(f"Redirecting to show {len(scraped_results)} accepted results")
        return redirect(f'/?product_id={product.id}')

    return redirect('dashboard')


def create_alert(request):
    """Handle alert creation form submission."""
    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        email = request.POST.get('email')
        target_price = request.POST.get('target_price')

        if product_id and email and target_price:
            try:
                product = Product.objects.get(pk=product_id)
                PriceAlert.objects.create(
                    product=product,
                    email=email,
                    target_price=target_price
                )
                print(f"Alert created for {email} on {product.name} at {target_price}")

                try:
                    parsed_target = Decimal(str(target_price)).quantize(Decimal('0.01'))
                except (InvalidOperation, TypeError):
                    parsed_target = None

                if parsed_target is not None:
                    matching_result = PriceResult.objects.filter(
                        product=product,
                        price__lte=parsed_target
                    ).order_by('price').first()

                    if matching_result:
                        from .services.tracker import check_alerts

                        alert_result = check_alerts(product, matching_result.price, matching_result.url)
                        if alert_result['sent']:
                            messages.success(
                                request,
                                f'Alert created and triggered immediately. Sent {alert_result["sent"]} email(s).'
                            )
                        elif alert_result['failed']:
                            messages.error(
                                request,
                                f'Alert matched right away, but email sending failed: {alert_result["errors"][0]["message"]}'
                            )
                        else:
                            messages.success(request, 'Alert created successfully.')
                    else:
                        messages.success(
                            request,
                            f'Alert created. It will trigger when a saved price drops to ₹{parsed_target}.'
                        )
                else:
                    messages.success(request, 'Alert created successfully.')
                return redirect(f'/?product_id={product.id}')
            except Product.DoesNotExist:
                pass

    return redirect('dashboard')


def price_editor(request, product_id):
    """Allow manual editing of saved prices for alert testing."""
    product = get_object_or_404(Product, pk=product_id)

    if request.method == 'POST':
        result_id = request.POST.get('result_id')
        price_value = request.POST.get('price', '').strip()
        price_result = PriceResult.objects.filter(pk=result_id, product=product).first()

        if not price_result:
            messages.error(request, 'Price entry not found for this product.')
            return redirect('price_editor', product_id=product.id)

        try:
            updated_price = Decimal(price_value)
        except (InvalidOperation, TypeError):
            messages.error(request, 'Enter a valid numeric price before saving.')
            return redirect('price_editor', product_id=product.id)

        if updated_price <= 0:
            messages.error(request, 'Price must be greater than zero.')
            return redirect('price_editor', product_id=product.id)

        updated_price = updated_price.quantize(Decimal('0.01'))
        old_price = price_result.price

        price_result.price = updated_price
        price_result.scraped_at = timezone.now()
        price_result.save(update_fields=['price', 'scraped_at'])

        PriceHistory.objects.create(
            product=product,
            website=price_result.website,
            price=updated_price
        )

        from .services.tracker import check_alerts

        alert_result = check_alerts(product, updated_price, price_result.url)
        summary = (
            f'Updated {price_result.website} from ₹{old_price} to ₹{updated_price}. '
            'Saved a price-history entry and checked alerts.'
        )

        if alert_result['sent']:
            messages.success(request, f'{summary} Sent {alert_result["sent"]} alert email(s).')
        elif alert_result['failed']:
            details = '; '.join(
                f'{item["email"]}: {item["message"]}' for item in alert_result['errors']
            )
            messages.error(request, f'{summary} Alert matched, but email failed. {details}')
        elif alert_result['matched']:
            messages.error(request, f'{summary} Alert matched, but the email result was inconclusive.')
        else:
            messages.success(request, f'{summary} No active alerts matched this price.')

        return redirect('price_editor', product_id=product.id)

    price_results = list(PriceResult.objects.filter(product=product).order_by('price', 'website'))
    active_alerts = list(PriceAlert.objects.filter(product=product, is_active=True).order_by('target_price', 'created_at'))
    best_result = find_best_price(price_results)

    context = {
        'product': product,
        'price_results': price_results,
        'active_alerts': active_alerts,
        'best_result': best_result,
    }
    return render(request, 'price_editor.html', context)
