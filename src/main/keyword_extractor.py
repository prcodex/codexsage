"""
Hybrid keyword extraction with enhanced filtering
Option C: Best balance of cost and quality
"""

import re
import json
import os
from anthropic import Anthropic

def load_exclusions():
    """Load exclusion terms from JSON file"""
    try:
        with open('keyword_exclusions.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        # Flatten all categories into one list
        exclusions = []
        for category in data.values():
            exclusions.extend(category)
        return exclusions
    except:
        # Fallback to minimal list if file doesn't exist
        return ['Breaking News', 'Market Updates', 'Analysis', 'News']

def regex_prefilter(text):
    """
    Simple regex pre-filter to remove common generic patterns
    This runs BEFORE AI extraction to reduce noise
    """
    # Remove common generic phrases
    patterns = [
        r'\b(breaking|latest|top|key)\s+(news|updates?|headlines?)\b',
        r'\bmarket\s+(updates?|news|highlights?|roundup)\b',
        r'\b(daily|weekly|monthly)\s+(brief|report|summary)\b',
        r'\b(today\'?s?|this\s+week\'?s?)\s+\w+\b',
    ]
    
    cleaned = text
    for pattern in patterns:
        cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
    
    return cleaned

def extract_keywords(title, content, sender_tag=""):
    """
    Extract meaningful keywords using hybrid approach:
    1. Regex pre-filter (remove generic patterns)
    2. AI extraction with enhanced prompt
    3. Post-processing filter (remove exclusion list)
    """
    
    client = Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY'))
    
    # Step 1: Pre-filter with regex
    cleaned_title = regex_prefilter(title)
    cleaned_content = regex_prefilter(content[:2000])
    
    text_sample = f"Title: {cleaned_title}\n\nContent: {cleaned_content}"
    
    # Detect language
    is_portuguese = any(word in content.lower() for word in ['notícias', 'hoje', 'brasil', 'semana'])
    
    # Step 2: Enhanced AI extraction with concrete examples
    prompt = f"""Extract 4-6 SPECIFIC KEYWORDS from this financial story.

✅ GOOD KEYWORDS (concrete and specific):
- Company names: "Apple", "Tesla", "Boston Scientific", "Petrobras"
- Specific topics: "AI Chips", "Trade War", "Nuclear Energy", "Interest Rate Cut"
- People: "Jerome Powell", "Elon Musk", specific CEOs
- Places: "China", "Brazil", "Federal Reserve", "Silicon Valley"
- Specific concepts: "Rare Earth Metals", "Tariffs", "Inflation Target"

❌ BAD KEYWORDS (too generic - AVOID):
- "Breaking News", "Market Updates", "Analysis", "Report"
- "Notícias", "Análise", "Mercado", "Resumo"
- "Markets", "Trading", "Investors", "Today"
- "Updates", "Highlights", "Coverage", "Outlook"

FOCUS ON: What is the story ABOUT (specific entities, events, concepts)
NOT: How it's presented (news, update, report, etc.)

{"This is Portuguese content. Extract keywords in Portuguese." if is_portuguese else ""}

Return ONLY the keywords separated by " • " (bullet with spaces).
Maximum 6 keywords. Be specific and concrete.

Story:
{text_sample}

Keywords:"""

    try:
        response = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=150,
            messages=[{"role": "user", "content": prompt}]
        )
        
        keywords = response.content[0].text.strip()
        
        # Clean up the response
        keywords = keywords.replace('\n', ' • ')
        keywords = keywords.strip('•').strip()
        
        # Step 3: Post-processing filter with exclusion list
        exclusions = load_exclusions()
        
        # Split into individual keywords
        keyword_list = [k.strip() for k in keywords.split('•')]
        
        # Filter out exclusions (case-insensitive)
        filtered_keywords = []
        for kw in keyword_list:
            # Check if keyword is in exclusion list (case-insensitive)
            if not any(excl.lower() == kw.lower() for excl in exclusions):
                # Also check if it's a substring match for multi-word exclusions
                is_excluded = False
                for excl in exclusions:
                    if len(excl.split()) > 1:  # Multi-word exclusion
                        if excl.lower() in kw.lower() or kw.lower() in excl.lower():
                            is_excluded = True
                            break
                if not is_excluded:
                    filtered_keywords.append(kw)
        
        # Rejoin filtered keywords
        result = ' • '.join(filtered_keywords)
        
        # Clean up double bullets and spaces
        result = re.sub(r'\s*•\s*•\s*', ' • ', result)
        result = result.strip(' •').strip()
        
        # If we filtered everything out, return a generic fallback
        if not result:
            return "Financial News" if not is_portuguese else "Notícias Financeiras"
        
        return result
        
    except Exception as e:
        print(f"Error extracting keywords: {e}")
        return "Financial News" if not is_portuguese else "Notícias Financeiras"
