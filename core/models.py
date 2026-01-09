from django.db import models
from django.utils import timezone


class Product(models.Model):
    """Model to store product search queries."""
    name = models.CharField(max_length=255)
    search_query = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name


class PriceResult(models.Model):
    """Model to store price results from different websites."""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='price_results')
    website = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    url = models.URLField(max_length=500)
    image_url = models.URLField(max_length=500, null=True, blank=True)
    scraped_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['price']
    
    def __str__(self):
        return f"{self.product.name} - {self.website} - ₹{self.price}"


class PriceHistory(models.Model):
    """Model to store historical price data points."""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='price_history')
    website = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    timestamp = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-timestamp']
        verbose_name_plural = "Price histories"

    def __str__(self):
        return f"{self.product.name} - {self.website} - ₹{self.price} ({self.timestamp.strftime('%Y-%m-%d')})"


class PriceAlert(models.Model):
    """Model to store user price alerts."""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='price_alerts')
    email = models.EmailField()
    target_price = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Alert for {self.email} on {self.product.name} (< ₹{self.target_price})"
