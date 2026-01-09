from django.core.management.base import BaseCommand
from core.models import Product
from core.services.tracker import track_prices_for_product
import time

class Command(BaseCommand):
    help = 'Scans all tracked products, updates prices, and sends alerts if thresholds are met.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--loop',
            type=int,
            help='Run in a loop with a specified delay (in seconds) between scans.',
        )

    def handle(self, *args, **options):
        loop_delay = options.get('loop')
        
        while True:
            try:
                products = Product.objects.all()
                total = products.count()
                
                self.stdout.write(self.style.SUCCESS(f'[{time.strftime("%Y-%m-%d %H:%M:%S")}] Starting price check for {total} products...'))
                
                for i, product in enumerate(products, 1):
                    self.stdout.write(f'[{i}/{total}] Checking: {product.name}...')
                    
                    try:
                        # Use the shared tracking service
                        results = track_prices_for_product(product)
                        
                        if results:
                            prices = [f"{r['website']}: {r['price']}" for r in results]
                            self.stdout.write(self.style.SUCCESS(f'  -> Updated: {", ".join(prices)}'))
                        else:
                            self.stdout.write(self.style.WARNING(f'  -> No results found'))
                            
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f'  -> Error: {str(e)}'))
                    
                    # Politeness delay between products
                    if i < total:
                        time.sleep(2)
                
                self.stdout.write(self.style.SUCCESS('Price check completed successfully.'))
                
                # Exit if not looping
                if not loop_delay:
                    break
                    
                self.stdout.write(self.style.WARNING(f'Sleeping for {loop_delay} seconds... (Ctrl+C to stop)'))
                time.sleep(loop_delay)
                self.stdout.write('\n')
                
            except KeyboardInterrupt:
                self.stdout.write(self.style.SUCCESS('\nUser interrupted. Exiting...'))
                break
