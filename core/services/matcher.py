import difflib

def calculate_match_score(query, title):
    """
    Calculate a similarity score between query and product title.
    Returns a float between 0.0 and 1.0.
    """
    if not query or not title:
        return 0.0
    
    query = query.lower().strip()
    title = title.lower().strip()
    
    # 0. Accessory Check (The "Sleeve" Defense)
    # If title contains accessory keywords but query doesn't, penalize heavily
    accessory_keywords = {'case', 'cover', 'sleeve', 'guard', 'screen protector', 'skin', 'pouch', 'bag'}
    query_words = set(query.split())
    title_words = set(title.split())
    
    is_accessory = False
    for word in accessory_keywords:
        if word in title_words and word not in query_words:
            is_accessory = True
            break
            
    if is_accessory:
        return 0.2 # Penalize score significantly
    
    # 1. Exact substring match
    if query in title:
        return 1.0
        
    # 2. Token overlap score
    query_tokens = [t for t in query.split() if len(t) > 1]
    if not query_tokens:
        return difflib.SequenceMatcher(None, query, title).ratio()
        
    matches = 0
    for token in query_tokens:
        if token in title:
            matches += 1
            
    token_score = matches / len(query_tokens)
    
    # 3. Sequence Similarity
    seq_score = difflib.SequenceMatcher(None, query, title).ratio()
    
    # Weighted average (Token match is more important for relevance)
    final_score = (token_score * 0.7) + (seq_score * 0.3)
    
    return final_score
