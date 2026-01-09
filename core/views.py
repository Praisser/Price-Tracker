from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
from django.core.mail import send_mail
from .models import Product, PriceResult, PriceHistory, PriceAlert
from .services.comparator import find_best_price, sort_by_price


def dashboard(request):
    """Display the main dashboard with search functionality."""
    context = {}
    
    # If there's a product_id in GET params, show results
    product_id = request.GET.get('product_id')
    error_param = request.GET.get('error')
    
    if product_id:
        try:
            product = Product.objects.get(pk=product_id)
            price_results = PriceResult.objects.filter(product=product)
            
            # Convert to list for sorting
            results_list = list(price_results)
            sorted_results = sort_by_price(results_list, ascending=True)
            
            # Find best price
            best_result = find_best_price(sorted_results)
            best_price = best_result.price if best_result else None
            
            # Add is_best flag to each result
            for result in sorted_results:
                result.is_best = (best_result and result.id == best_result.id)
            
            # Get all expected websites
            expected_websites = ['Amazon', 'Flipkart']
            found_websites = [r.website for r in sorted_results]
            missing_websites = [w for w in expected_websites if w not in found_websites]

            # --- Price History Logic ---
            # Fetch history for chart
            history_qs = PriceHistory.objects.filter(product=product).order_by('timestamp')
            
            # Transform for Chart.js: { 'Amazon': [{x: date, y: price}, ...], 'Flipkart': [...] }
            history_data = {}
            for entry in history_qs:
                if entry.website not in history_data:
                    history_data[entry.website] = []
                history_data[entry.website].append({
                    'x': entry.timestamp.isoformat(),
                    'y': float(entry.price)
                })
            
            # Pass data as simple lists for template (easier to iterate if using custom JS or just raw dump)
            # Actually, let's keep it dict-like or just JSON dumpable
            import json
            from django.core.serializers.json import DjangoJSONEncoder
            
            history_json = json.dumps(history_data, cls=DjangoJSONEncoder)

            context = {
                'product': product,
                'price_results': sorted_results,
                'best_result': best_result,
                'best_price': best_price,
                'has_results': len(sorted_results) > 0,
                'missing_websites': missing_websites,
                'total_expected': len(expected_websites),
                'total_found': len(sorted_results),
                'history_json': history_json  # Pass to template
            }
            
            # Add error message if no results
            if error_param == 'no_results' and not sorted_results:
                context['error'] = f'No prices found for "{product.name}". The product might not be available or the websites may have blocked the request. Please try again later or search for a different product.'
            elif missing_websites and sorted_results:
                # Some websites failed but we have some results
                context['warning'] = f'Found prices from {len(sorted_results)} website(s). Could not fetch from: {", ".join(missing_websites)}. This may be due to rate limiting or website blocking.'
        except Product.DoesNotExist:
            context['error'] = 'Product not found'
    
    return render(request, 'dashboard.html', context)


def search_product(request):
    """Handle product search and trigger scraping."""
    if request.method == 'POST':
        query = request.POST.get('query', '').strip()
        
        if not query:
            return redirect('dashboard')
        
        # Check for cached results (within cache expiry time)
        cache_hours = getattr(settings, 'CACHE_EXPIRY_HOURS', 6)
        cache_time = timezone.now() - timedelta(hours=cache_hours)
        
        # Try to find existing product with recent results
        product = Product.objects.filter(search_query__iexact=query).first()
        
        if product:
            recent_results = PriceResult.objects.filter(
                product=product,
                scraped_at__gte=cache_time
            )
            
            if recent_results.exists():
                # Use cached results
                return redirect(f'/?product_id={product.id}')
        
        # Create or get product
        if not product:
            product = Product.objects.create(
                name=query,
                search_query=query
            )
        else:
            # Clear old results if cache expired
            PriceResult.objects.filter(product=product).delete()
        
        # Use shared tracking service
        from .services.tracker import track_prices_for_product
        scraped_results = track_prices_for_product(product)
        
        # If no results found, still redirect but with a message
        if not scraped_results:
            print("No results found from any scraper")
            return redirect(f'/?product_id={product.id}&error=no_results')
        
        print(f"Redirecting to show {len(scraped_results)} results")
        # Redirect to dashboard with results
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
                return redirect(f'/?product_id={product.id}')
            except Product.DoesNotExist:
                pass
                
    return redirect('dashboard')
