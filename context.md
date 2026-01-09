# Project Context: Price Tracker

## Overview
A Django-based web application that tracks and compares product prices across **Amazon** and **Flipkart** in real-time. The project features a premium, minimal dark aesthetic ("Market Intelligence" theme).

## Recent Major Updates
### 1. UI/UX Overhaul (Premium Dark Theme)
- **Aesthetic**: Transformed from a basic interface to a luxury SaaS feel using `Inter` font, Glassmorphism, and a Midnight Black (`#0A0A0A`) background.
- **Key Files**: `core/static/css/style.css`, `core/templates/dashboard.html`.
- **Features**:
    - **Live Market Scan**: An overlay with a radar animation and terminal-style logs ("Connecting to Amazon... Decrypting...") that plays during the search process to mask latency and enhance immersion.

### 2. Scraper Intelligence (Flipkart)
- **Problem**: The scraper was returning irrelevant results (e.g., competing brands) because ads or sponsored items pushed exact matches down.
- **Solution**:
    - Increased scan depth from 8 to **40 results**.
    - Implemented a **relevance scoring system** that heavily weights brand matches (+50 points).
    - Added logic to find the "Best Match" rather than just the first result.
- **Key File**: `core/services/scraper/flipkart.py`.

### 3. Backend Caching
- **Logic**: Search results are cached for 6 hours (configurable).
- **Behavior**: If a user searches for a product again within the window, cached results are shown instantly. If the cache expires, old results are **deleted** and a fresh scrape is triggered.
- **Key File**: `core/views.py`.

## Technical Architecture
- **Framework**: Django 5.x
- **Database**: SQLite (Default)
- **Frontend**: Django Templates + Vanilla JS + CSS3 (Variables-based theming)
- **Scrapers**: `requests` + `BeautifulSoup` (with some Playwright capability for Amazon).

## Current Status (Active Features)
- [x] **Cross-Platform Search**: Simultaneously scrapes Amazon and Flipkart.
- [x] **Best Offer Detection**: Automatically highlights the lowest price.
- [x] **Live Scan UX**: Visual feedback system during scraping.
- [x] **Mobile Responsive**: Fully adaptive grid layout.

## Note on "Price History"
*A "Price Trend/History" feature was explored and implemented but subsequently reverted to maintain simplicity and storage efficiency. The system currently operates on a "Snapshot" model (latest price only).*
