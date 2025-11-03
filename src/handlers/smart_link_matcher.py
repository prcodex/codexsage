#!/usr/bin/env python3
"""
Smart link matcher - With full Portuguese support
"""

from bs4 import BeautifulSoup
import re
from difflib import SequenceMatcher

def similarity(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def extract_links_with_titles(html_content):
    """Extract links with their anchor text - ALL languages"""
    
    soup = BeautifulSoup(html_content, 'html.parser')
    links_data = []
    
    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href']
        text = a_tag.get_text(strip=True)
        
        if not href.startswith('http'):
            continue
        
        # Skip junk
        skip = ['unsubscribe', 'preference', 'settings', 'manage',
                'facebook.com', 'twitter.com', 'linkedin.com', 'instagram.com',
                'mailto:', 'View it in', 'Ver no navegador', 'acesse este link']
        
        if any(s in href.lower() or s in text.lower() for s in skip):
            continue
        
        # Accept tracking URLs from ALL sources (English + Portuguese)
        is_article = (
            # English sources
            'wsj.com/articles' in href or 'weekendreads.cmail' in href or 'email.wsj.com' in href or
            'bloomberg.com/news' in href or 'links.message.bloomberg.com' in href or
            'businessinsider.com' in href or 'l.businessinsider.com' in href or
            'reuters.com' in href or 'newslink.reuters.com' in href or
            'barrons.com' in href or 'barrons.cmail19.com' in href or
            # Portuguese sources
            'estadao.com.br' in href or 'click.jornal.estadao.com.br' in href or
            'folha' in href or 'click.folhadespaulo.com.br' in href
        )
        
        # Keep if article link and has text (even short text for Portuguese)
        if is_article and len(text) > 3:
            links_data.append({
                'url': href,
                'title': text,
                'text_lower': text.lower()
            })
    
    return links_data

def find_best_link_for_story(story_title, links_data):
    """Find best match - works for Portuguese and English"""
    
    story_clean = story_title.replace('📰 ', '').strip().lower()
    
    best_match = None
    best_score = 0
    
    for link_data in links_data:
        link_title = link_data['title'].lower()
        
        score = similarity(story_clean, link_title)
        
        # Word overlap
        story_words = set(re.findall(r'\w+', story_clean))
        link_words = set(re.findall(r'\w+', link_title))
        
        # Common words (Portuguese + English)
        common = {'the', 'a', 'an', 'and', 'or', 'in', 'on', 'at', 'to', 'for', 'of', 'is',
                 'o', 'a', 'os', 'as', 'de', 'da', 'do', 'das', 'dos', 'e', 'em', 'para'}
        story_words -= common
        link_words -= common
        
        if story_words and link_words:
            word_overlap = len(story_words & link_words) / len(story_words | link_words)
            combined_score = (score * 0.6) + (word_overlap * 0.4)
        else:
            combined_score = score
        
        if combined_score > best_score:
            best_score = combined_score
            best_match = link_data
    
    # Lower threshold for Portuguese (short link text)
    threshold = 0.25
    
    if best_score > threshold:
        return best_match['url'], best_score
    
    return None, 0
