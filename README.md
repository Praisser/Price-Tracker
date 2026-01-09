# Price Tracker - Market Intelligence Engine

A premium, Django-based market analysis tool that aggregates and compares prices across major e-commerce platforms. fast, accurate, and designed with a luxury dark aesthetic.

## Features

- 💎 **Premium Luxury UI** - Minimal, dark-themed interface inspired by Vercel and Linear (#0A0A0A).
- 🧠 **Smart Relevance Engine** - Intelligently filters search results (scans top 40 items) to exclude ads and irrelevant competitor products.
- 🔍 **Real-time Search** - Live pricing from Amazon and Flipkart.
- ⚡ **Performance Caching** - Results are cached for 6 hours for instant subsequent loads.
- 📱 **Responsive & Glassmorphism** - Modern, fluid design that works on all devices.
- 🎯 **Best Deal Recommendation** - Automatically highlights the optimal purchase choice.

## Supported Websites

- **Amazon.in** (with Playwright fallback for reliability)
- **Flipkart.com** (with relevance scoring to filter "Sponsored" items)

## Technology Stack

- **Backend**: Django 4.2+
- **Scraping**: BeautifulSoup4, Requests, Playwright
- **UI/UX**: HTML5, CSS3 (Variables, Glassmorphism, Animations)
- **Database**: SQLite (default) / PostgreSQL

## Installation

### Prerequisites

- Python 3.10 or higher
- pip (Python package manager)

### Setup Steps

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Price-Tracker
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # Linux/Mac
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Install Playwright (Required for Amazon)**
   ```bash
   python -m playwright install chromium
   ```

5. **Run migrations**
   ```bash
   python manage.py migrate
   ```

6. **Run the development server**
   ```bash
   python manage.py runserver
   ```

7. **Access the application**
   - Dashboard: `http://127.0.0.1:8000/`

## Usage

1. Enter a product name in the glowing search bar (e.g., "MacBook Air M3").
2. The engine scans multiple retailers and filters for the specific brand/model.
3. Compare prices in the sleek horizontal card view.
4. Use the "Secure This Price" button on the recommended offer.

## Project Structure

```
price_tracker/
├── core/
│   ├── services/
│   │   ├── scraper/         # Amazon & Flipkart scrapers
│   │   ├── normalizer.py    # Data standardization
│   │   └── comparator.py    # Price logic
│   ├── templates/           # Premium HTML templates
│   └── static/              # CSS & Animations
└── manage.py
```

## Caching Strategy

To ensure speed and politeness to target sites:
- Search results are cached for **6 hours**.
- Repeated searches for the same term hit the database instantly.

## Disclaimer

This tool is for educational purposes only. Web scraping should be done in compliance with the terms of service of the target websites.

---

**© 2026 Price Tracker**
