// Price Tracker - Main JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Auto-focus search input
    const searchInput = document.querySelector('.search-input');
    if (searchInput) {
        searchInput.focus();
    }

    // Add loading state to search button
    const searchForm = document.querySelector('.search-form');
    if (searchForm) {
        searchForm.addEventListener('submit', function(e) {
            const searchBtn = this.querySelector('.search-btn');
            const searchInput = this.querySelector('.search-input');
            const originalBtnContent = searchBtn.innerHTML;
            
            if (searchBtn && searchInput.value.trim()) {
                searchBtn.disabled = true;
                searchBtn.style.opacity = '0.7';
                searchBtn.innerHTML = '<span class="search-icon">⏳</span> <span>Searching...</span>';
                
                // Add loading overlay to results if refreshing
                const resultsWrapper = document.querySelector('.results-wrapper');
                if (resultsWrapper) {
                    resultsWrapper.style.opacity = '0.5';
                    resultsWrapper.style.pointerEvents = 'none';
                }
            }
        });
    }

    // Smooth scroll to results if they exist
    const resultsWrapper = document.querySelector('.results-wrapper');
    if (resultsWrapper) {
        // Add a small delay to ensure rendering is complete
        setTimeout(() => {
            const headerOffset = 100; // Adjust based on header height
            const elementPosition = resultsWrapper.getBoundingClientRect().top;
            const offsetPosition = elementPosition + window.pageYOffset - headerOffset;
        
            window.scrollTo({
                top: offsetPosition,
                behavior: "smooth"
            });
        }, 100);

        // Staggered animation for table rows
        const tableRows = document.querySelectorAll('.compare-table tbody tr');
        tableRows.forEach((row, index) => {
            row.style.opacity = '0';
            row.style.transform = 'translateY(20px)';
            
            setTimeout(() => {
                row.style.transition = 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)';
                row.style.opacity = '1';
                row.style.transform = 'translateY(0)';
            }, 100 + (index * 50)); // Faster stagger
        });
        
        // Best deal card animation
        const bestDealCard = document.querySelector('.best-deal-card');
        if (bestDealCard) {
            bestDealCard.style.opacity = '0';
            bestDealCard.style.transform = 'translateY(30px)';
            setTimeout(() => {
                bestDealCard.style.transition = 'all 0.6s cubic-bezier(0.175, 0.885, 0.32, 1.275)';
                bestDealCard.style.opacity = '1';
                bestDealCard.style.transform = 'translateY(0)';
            }, 600);
        }
    }

    // Features animation
    const features = document.querySelectorAll('.feature-card');
    if (features.length > 0) {
        features.forEach((feature, index) => {
            feature.style.opacity = '0';
            feature.style.transform = 'translateY(30px)';
            setTimeout(() => {
                feature.style.transition = 'all 0.5s ease-out';
                feature.style.opacity = '1';
                feature.style.transform = 'translateY(0)';
            }, 200 + (index * 100));
        });
    }
});
