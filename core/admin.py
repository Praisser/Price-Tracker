from django.contrib import admin
from .models import Product, PriceResult, SourceStatus


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'search_query', 'created_at']
    search_fields = ['name', 'search_query']


@admin.register(PriceResult)
class PriceResultAdmin(admin.ModelAdmin):
    list_display = ['product', 'website', 'title', 'price', 'match_confidence', 'scraped_at']
    list_filter = ['website', 'scraped_at']
    search_fields = ['product__name', 'website', 'title']


@admin.register(SourceStatus)
class SourceStatusAdmin(admin.ModelAdmin):
    list_display = ['product', 'website', 'state', 'match_confidence', 'http_status', 'checked_at']
    list_filter = ['website', 'state', 'checked_at']
    search_fields = ['product__name', 'website', 'matched_title', 'diagnostic_message']
