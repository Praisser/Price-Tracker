from django.contrib import admin
from .models import Product, PriceResult


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'search_query', 'created_at']
    search_fields = ['name', 'search_query']


@admin.register(PriceResult)
class PriceResultAdmin(admin.ModelAdmin):
    list_display = ['product', 'website', 'price', 'scraped_at']
    list_filter = ['website', 'scraped_at']
    search_fields = ['product__name', 'website']
