from core.services.matcher import calculate_match_score

def debug_m4_case():
    query = "MacBook Air M4"
    # Title taken from user metadata (Page 72040...)
    title = "Buy DailyObjects Unisex Skipper Sleeve Medium For MacBook Air/Pro 33.02cm (13 Inch)"
    
    print(f"Query: {query}")
    print(f"Title: {title}")
    
    score = calculate_match_score(query, title)
    print(f"Calculated Score: {score}")
    
    # Check logic flow
    if score < 0.2:
        print("Result: REJECTED (Score < 0.2)")
    elif score >= 0.5:
        print("Result: ACCEPTED (Single Result Score >= 0.5)")
    else:
        print("Result: REJECTED (Single Result Score < 0.5)")

if __name__ == "__main__":
    debug_m4_case()
