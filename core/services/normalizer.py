"""
Data normalization service to standardize scraped data.
"""


def normalize_price_data(data):
    """
    Normalize scraped price data to a standard format.
    
    Args:
        data: Dictionary with website, price, url, title
        
    Returns:
        dict: Normalized data or None if invalid
    """
    if not data or not isinstance(data, dict):
        return None
    
    # Ensure required fields
    required_fields = ['website', 'price', 'url']
    if not all(field in data for field in required_fields):
        return None
    
    # Validate price
    try:
        price = float(data['price'])
        if price <= 0:
            return None
    except (ValueError, TypeError):
        return None
    
    # Validate URL
    url = data['url']
    if not url or not url.startswith(('http://', 'https://')):
        return None
    
    # Return normalized data
    return {
        'website': str(data['website']).strip(),
        'price': price,
        'url': url.strip(),
        'title': data.get('title', '').strip(),
        'image_url': data.get('image_url')
    }
