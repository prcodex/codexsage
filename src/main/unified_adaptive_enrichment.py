from html_text_extractor import get_best_content
#!/usr/bin/env python3
"""
SCRAPEX - Simple TAG → RULE Enrichment System
Uses direct table lookup instead of complex detection logic
"""

import lancedb
from keyword_extractor import extract_keywords
import pandas as pd
import os
import sys
from datetime import datetime
import pytz

# Import all handlers
from wsj_teaser_handler import enrich_wsj_teaser
from rosenberg_deep_research_handler import enrich_rosenberg_deep_research
from breakfast_with_dave_handler import enrich_breakfast_with_dave
from newsbrief_with_links_handler import enrich_newsbrief_with_links
from newsbrief_with_links_handler import enrich_newsbrief_with_links
from gold_standard_enhanced_handler import enrich_gold_standard_enhanced
from tony_pasquariello_handler import enrich_tony_pasquariello
from cochrane_detailed_summary_handler import enrich_cochrane_detailed
from itau_daily_handler import enrich_itau_daily
from shadow_handler import enrich_shadow_price
from macrocharts_handler import enrich_macro_charts
from elerian_rep_handler import enrich_elerian_rep

# ══════════════════════════════════════════════════════════════════════════════
# TAG → RULE MAPPING TABLE
# ══════════════════════════════════════════════════════════════════════════════

TAG_TO_RULE = {
    # Special cases
    "WSJ Opinion": "wsj_opinion",
    
    # Rosenberg
    "Rosenberg_EM": "rosenberg_deep_research",
    "Rosenberg Research": "breakfast_headlines",
    
    # NewsBrief Portuguese
    "Folha": "newsbrief_portuguese",
    "Estadão": "newsbrief_portuguese_with_links",  # With clickable links!
    "O Globo": "newsbrief_portuguese",
    
    # NewsBrief English
    "WSJ": "newsbrief_english",
    "Financial Times / FT": "newsbrief_english",
    "Reuters": "newsbrief_english",
    "Bloomberg": "newsbrief_english",
    "Business Insider": "newsbrief_english",
    "Barons Daily": "newsbrief_english",
    "TKer": "newsbrief_english",
    "Topdown Charts": "newsbrief_english",
    "Macro Mornings": "newsbrief_english",
    
    # Gold Standard Enhanced
    "Goldman Sachs": "gold_standard_enhanced",
    "Torsten Slok": "gold_standard_enhanced",
    "Adam Tooze": "gold_standard_enhanced",
    "Noahpinion": "gold_standard_enhanced",
    "Yascha Mounk": "gold_standard_enhanced",
    "MacroTourist": "gold_standard_enhanced",
    "Matt Stoller": "gold_standard_enhanced",
    
    # Specialized
    "John Cochrane": "cochrane_detailed",
    
    # Itau (7 types, same rule, language-aware)
    "Itau_FOMC": "itau_daily",
    "Itau_China": "itau_daily",
    "Itau_Europe": "itau_daily",
    "Itau_Brazil_Daily": "itau_daily",
    "Itau_Global": "itau_daily",
    "Itau_Cac": "itau_daily",
    "Itau": "itau_daily",
    "Shadow Price Macro": "shadow_vlm",
    "Macro Charts": "charts_vlm",
    "ChartStorm": "charts_vlm",
    "Mohamed El-Erian": "elerian_rep",
}


def apply_rule(tag, rule, title, content_text, content_html, api_key):
    """
    Apply the enrichment rule based on tag
    Simple switch statement - no complex detection!
    """
    
    print(f"   📋 Tag: {tag} → Rule: {rule}")
    
    try:
        # WSJ Opinion (title-only, no AI)
        if rule == "wsj_opinion":
            return enrich_wsj_teaser(title, content_html)
        
        # Rosenberg Deep Research
        elif rule == "rosenberg_deep_research":
            return enrich_rosenberg_deep_research(title, content_text, api_key)
        
        # Rosenberg Breakfast Headlines
        elif rule == "breakfast_headlines":
            return enrich_breakfast_with_dave(title, content_html)
        
        # NewsBrief (Portuguese or English)
        elif rule in ["newsbrief_portuguese", "newsbrief_english"]:
            return enrich_newsbrief_with_links(title, content_text, tag, api_key)
        
        elif rule in ["newsbrief_portuguese_with_links", "newsbrief_english_with_links"]:
            return enrich_newsbrief_with_links(title, content_text, tag, api_key)
        
        # Gold Standard Enhanced
        elif rule == "gold_standard_enhanced":
            return enrich_gold_standard_enhanced(title, content_text, tag, api_key)
        
        # Cochrane Detailed
        elif rule == "cochrane_detailed":
            return enrich_cochrane_detailed(title, content_text, api_key)
        
        # Itau Daily
        elif rule == "itau_daily":
            return enrich_itau_daily(title, content_text, content_html, tag, api_key)
        
        # Shadow Price Macro (VLM)
        elif rule == "shadow_vlm":
            return enrich_shadow_price(title, content_text, content_html, api_key)
        
        # Macro Charts (VLM)
        elif rule == "charts_vlm":
            return enrich_macro_charts(title, content_text, content_html, api_key)
        
        # El-Erian REP
        elif rule == "elerian_rep":
            return enrich_elerian_rep(title, content_text, api_key)
        
        # Tony Pasquariello (Goldman Sachs subclass)
        elif rule == "tony_pasquariello":
            return enrich_tony_pasquariello(title, content_text, api_key)
        
        
        # Default fallback
        else:
            print(f"   ⚠️  Unknown rule: {rule}, using Gold Standard")
            return enrich_gold_standard_enhanced(title, content_text, tag, api_key)
    
    except Exception as e:
        print(f"   ❌ Handler error: {e}")
        # Return empty result instead of failing
        return {
            'smart_summary': "Rule: Error\n\n❌ Enrichment failed: " + str(e)[:200],
            'actors': [],
            'themes': [],
            'smart_category': 'ERROR',
            'ai_relevance_score': 5.0
        }


def enrich_items(last_n=None):
    """
    Main enrichment function - SIMPLE TAG → RULE routing
    """
    
    print("\n" + "="*80)
    print("SCRAPEX SIMPLE TAG → RULE ENRICHMENT")
    print("="*80)
    print(f"Time: {datetime.now()}\n")
    
    # Connect to database
    db = lancedb.connect("s3://sage-unified-feed-lance/lancedb/")
    tbl = db.open_table("unified_feed")
    df = tbl.to_pandas()
    
    # Convert timestamp
    df['created_at'] = pd.to_datetime(df['created_at'], format='mixed', errors='coerce', utc=True)
    
    # Sort by newest first
    df = df.sort_values('created_at', ascending=False)
    
    # Limit if requested
    if last_n:
        df = df.head(last_n)
        print(f"MODE: Backlog - Processing last {last_n} emails")
    else:
        print(f"MODE: All emails")
    
    print(f"Items to check: {len(df)}\n")
    
    # Get API key
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        print("❌ Error: ANTHROPIC_API_KEY not found")
        return
    
    enriched = 0
    skipped = 0
    
    for idx, row in df.iterrows():
        # Get fields
        item_id = row.get('id', '')
        tag = str(row.get('display_name', 'Unknown'))
        title = str(row.get('title', ''))
        content_text = str(row.get('content_text', ''))
        content_html = str(row.get('content_html', ''))
        
        # CRITICAL FIX (Oct 29): Extract from HTML if content_text is empty
        # Prevents hallucination when content_text is not populated by fetcher
        if not content_text or len(content_text.strip()) < 100:
            if content_html and len(content_html) > 100:
                try:
                    # Extract clean text from HTML using BeautifulSoup
                    from bs4 import BeautifulSoup
                    import re
                    
                    soup = BeautifulSoup(content_html, 'html.parser')
                    # Remove script and style elements
                    for script in soup(["script", "style"]):
                        script.decompose()
                    
                    # Get text
                    extracted_text = soup.get_text(separator='\n', strip=True)
                    # Clean up multiple newlines
                    extracted_text = re.sub(r'\n\s*\n+', '\n\n', extracted_text)
                    
                    if len(extracted_text) > 100:
                        content_text = extracted_text
                        print(f"   ⚠️  Extracted {len(content_text)} chars from HTML (content_text was empty)")
                except Exception as e:
                    print(f"   ❌ HTML extraction failed: {e}")
        
        current_summary = str(row.get('smart_summary', ''))
        
        # Skip if already enriched (has Rule: label and content)
        if current_summary and len(current_summary) > 100 and "Rule:" in current_summary:
            skipped += 1
            continue
        
        print(f"{tag} - {title[:60]}")
        
        # Look up rule for this tag
        rule = TAG_TO_RULE.get(tag, "gold_standard_enhanced")
        
        # Apply rule
        try:
            result = apply_rule(tag, rule, title, content_text, content_html, api_key)
            
            # Handle result (can be dict or tuple)
            if isinstance(result, dict):
                summary = result.get('smart_summary', '')
                actors = result.get('actors', [])
                themes = result.get('themes', [])
                category = result.get('smart_category', 'ANALYSIS')
                score = result.get('ai_relevance_score', 8.0)
            elif isinstance(result, tuple) and len(result) >= 5:
                summary, actors, themes, category, score = result[:5]
            else:
                print(f"   ❌ Unexpected result format")
                continue
            
            # Convert lists to strings if needed
            if isinstance(actors, list):
                actors = str(actors)
            if isinstance(themes, list):
                themes = str(themes)
            
            # Extract smart keywords (replaces actors/themes)
            print(f"   🔑 Extracting keywords...")
            keywords = extract_keywords(title, content_text, tag)
            print(f"   🔑 Keywords: {keywords}")
            
            # Update database with smart summary and keywords
            # Also store in enriched_content for display
            tbl.update(
                where=f"id = '{item_id}'",
                values={
                    'enriched_content': summary,  # Store in enriched_content for display
                    'smart_summary': summary,     # Also keep in smart_summary
                    'actors': keywords,           # Store keywords in actors field
                    'themes': '',                 # Clear themes
                    'ai_relevance_score': float(score)
                }
            )
            
            print(f"   ✅ {len(summary)} chars\n")
            enriched += 1
            
        except Exception as e:
            print(f"   ❌ Error: {e}\n")
            continue
    
    print("\n" + "="*80)
    print(f"✅ Enriched {enriched}/{len(df)} items")
    print(f"⏭️  Skipped {skipped} (already enriched)")
    print("="*80)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='SCRAPEX Simple Enrichment')
    parser.add_argument('--last', type=int, help='Process last N emails')
    
    args = parser.parse_args()
    
    enrich_items(last_n=args.last)
