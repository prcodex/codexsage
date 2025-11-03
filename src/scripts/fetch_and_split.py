#!/usr/bin/env python3
"""
SAGE Fetch and Split - With Portuguese Support
Complete flow: Gmail → Tag → Enrich → Split NewsBreif → Save
"""

import imaplib
import email
from email.header import decode_header
from bs4 import BeautifulSoup
import re
from datetime import datetime, timedelta, timezone
import lancedb
import pandas as pd
import os
import sys
import urllib.parse

sys.path.insert(0, '/home/ubuntu/newspaper_project')

from newsbrief_handler import enrich_newsbrief_with_links
from smart_link_matcher import extract_links_with_titles, find_best_link_for_story

# Configuration
GMAIL_USER = os.environ.get('GMAIL_USER', 'your_email@gmail.com')
GMAIL_PASSWORD = os.environ.get('GMAIL_APP_PASSWORD', 'YOUR_GMAIL_APP_PASSWORD_HERE')
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')

# Allowed sources (English + Portuguese)
ALLOWED_SOURCES = ['bloomberg', 'wsj', 'wall street', 'reuters', 'business insider', 
                   'barron', 'financial times', 'ft.com', 'rosenberg', 'goldman',
                   'itau', 'estadao', 'estadão', 'folha', 'folhadespaulo']

def detect_sender_tag(sender):
    """Detect sender tag"""
    sender_lower = sender.lower()
    
    if 'bloomberg' in sender_lower:
        return 'Bloomberg'
    elif 'wsj' in sender_lower or 'wall street' in sender_lower:
        return 'WSJ'
    elif 'reuters' in sender_lower:
        return 'Reuters'
    elif 'insider' in sender_lower:
        return 'Business Insider'
    elif 'barron' in sender_lower:
        return "Barron's"
    elif 'ft.com' in sender_lower or 'financial times' in sender_lower:
        return 'Financial Times'
    elif 'goldman' in sender_lower:
        return 'Goldman Sachs'
    elif 'rosenberg' in sender_lower:
        return 'Rosenberg Research'
    elif 'itau' in sender_lower or 'itaú' in sender_lower:
        return 'Itau'
    elif 'estadao' in sender_lower or 'estadão' in sender_lower:
        return 'Estadão'
    elif 'folha' in sender_lower:
        return 'Folha'
    else:
        return 'General'

def is_newsbrief_source(sender_tag):
    """Check if source should use NewsBreif handler (English + Portuguese)"""
    newsbrief_sources = ['Bloomberg', 'WSJ', 'Reuters', 'Business Insider', "Barron's", 
                        'Financial Times', 'Estadão', 'Folha']
    return sender_tag in newsbrief_sources

def fetch_and_process_emails(num_emails=10):
    """Complete flow with Portuguese support"""
    
    print(f"📬 Connecting to Gmail...")
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(GMAIL_USER, GMAIL_PASSWORD)
    mail.select("inbox")
    
    date_5_days = (datetime.now() - timedelta(days=5)).strftime("%d-%b-%Y")
    _, search_data = mail.search(None, f'(SINCE {date_5_days})')
    email_ids = search_data[0].split()
    
    print(f"Found {len(email_ids)} recent emails")
    print(f"Processing last {num_emails}...\n")
    
    all_stories = []
    processed = 0
    
    for email_id in list(reversed(email_ids))[:num_emails*3]:
        if processed >= num_emails:
            break
        
        try:
            _, msg_data = mail.fetch(email_id, "(RFC822)")
            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)
            
            sender = msg.get("From", "")
            
            if not any(source in sender.lower() for source in ALLOWED_SOURCES):
                continue
            
            # Get subject
            subject_header = msg.get("Subject", "")
            if subject_header:
                subject_decoded = decode_header(subject_header)
                subject = ""
                for part, encoding in subject_decoded:
                    if isinstance(part, bytes):
                        subject += part.decode(encoding or "utf-8", errors="ignore")
                    else:
                        subject += str(part)
            else:
                continue
            
            subject = subject.strip()
            
            # Get date
            date_str = msg.get("Date", "")
            try:
                from email.utils import parsedate_to_datetime
                date_obj = parsedate_to_datetime(date_str)
                created_at = date_obj.isoformat()
            except:
                created_at = datetime.now(timezone.utc).isoformat()
            
            # Get content
            content_text = ""
            content_html = ""
            
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        payload = part.get_payload(decode=True)
                        if payload:
                            content_text = payload.decode("utf-8", errors="ignore")
                    elif part.get_content_type() == "text/html":
                        payload = part.get_payload(decode=True)
                        if payload:
                            content_html = payload.decode("utf-8", errors="ignore")
            
            sender_tag = detect_sender_tag(sender)
            
            print(f"{processed+1}. [{sender_tag:18}] {subject[:40]}")
            
            # Extract links
            links_data = extract_links_with_titles(content_html)
            print(f"   Article links: {len(links_data)}")
            
            # Enrich
            if is_newsbrief_source(sender_tag):
                to_enrich = content_text or content_html[:10000]
                enriched = enrich_newsbrief_with_links(subject, to_enrich, sender_tag, ANTHROPIC_API_KEY)
                
                # Split into stories
                pattern = r'<strong[^>]*?>(\d+)\.(.*?)</strong>(.*?)(?=<strong[^>]*?>\d+\.|$)'
                matches = re.findall(pattern, enriched, re.DOTALL)
                
                if matches:
                    print(f"   Stories extracted: {len(matches)}")
                    
                    for i, (num, story_title, story_content) in enumerate(matches):
                        clean_title = story_title.strip()
                        clean_content = re.sub(r'<[^>]+>', '', story_content).strip()
                        
                        # Match link (works for Portuguese too!)
                        matched_url, confidence = find_best_link_for_story(clean_title, links_data)
                        
                        if matched_url and confidence > 0.25:  # Lower threshold for Portuguese
                            clean_content += f'\n\n🔗 <a href="{matched_url}" target="_blank" style="color: #1DA1F2; text-decoration: none;">Ler artigo completo</a>'
                            link_status = f'REAL ({confidence:.0%})'
                        else:
                            search_query = urllib.parse.quote(clean_title)
                            clean_content += f'\n\n🔗 <a href="https://news.google.com/search?q={search_query}" target="_blank" style="color: #1DA1F2; text-decoration: none;">Buscar no Google Notícias</a>'
                            link_status = 'Google'
                        
                        story = {
                            'id': f'email_{processed}_story_{i}',
                            'source_type': 'email',
                            'created_at': created_at,
                            'author': sender,
                            'author_email': sender,
                            'title': f'📰 {clean_title}',
                            'content_text': clean_content,
                            'content_html': content_html[:50000],  # Store original email HTML
                            'sender_tag': f'{sender_tag}- Newsbrief',
                            'ai_score': 8.0,
                            'ai_relevance_score': 8.0,
                            'enriched_content': clean_content,
                            'actors': f'{sender_tag} Repórteres • Equipe' if sender_tag in ['Estadão', 'Folha'] else f'{sender_tag} Reporters • News Team',
                            'themes': 'Notícias • Mercados • Economia' if sender_tag in ['Estadão', 'Folha'] else 'Breaking News • Market Updates'
                        }
                        
                        all_stories.append(story)
                        print(f"      {i+1}. {clean_title[:35]} [{link_status}]")
                
                else:
                    # Single article
                    enriched_clean = re.sub(r'Rule: NewsBrief\n+', '', enriched)
                    
                    story = {
                        'id': f'email_{processed}',
                        'source_type': 'email',
                        'created_at': created_at,
                        'author': sender,
                        'author_email': sender,
                        'title': subject,
                        'content_text': content_text[:5000],
                        'content_html': content_html[:50000],  # Store original email HTML
                        'sender_tag': sender_tag,
                        'ai_score': 7.5,
                        'ai_relevance_score': 7.5,
                        'enriched_content': enriched_clean,
                        'actors': f'{sender_tag} Team',
                        'themes': 'Financial News'
                    }
                    
                    all_stories.append(story)
                    print(f"   Single article")
            
            else:
                # Basic enrichment
                basic_content = f'📰 {subject}\n\n• Conteúdo de {sender_tag}' if sender_tag in ['Estadão', 'Folha'] else f'📰 {subject}\n\n• Article from {sender_tag}'
                
                story = {
                    'id': f'email_{processed}',
                    'source_type': 'email',
                    'created_at': created_at,
                    'author': sender,
                    'author_email': sender,
                    'title': subject,
                    'content_text': content_text[:5000],
                    'content_html': content_html[:50000],  # Store original email HTML
                    'sender_tag': sender_tag,
                    'ai_score': 7.0,
                    'ai_relevance_score': 7.0,
                    'enriched_content': basic_content,
                    'actors': sender_tag,
                    'themes': 'Financial Analysis'
                }
                
                all_stories.append(story)
                print(f"   Basic enrichment")
            
            processed += 1
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            continue
    
    mail.close()
    mail.logout()
    
    if all_stories:
        print(f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"💾 Creating database with {len(all_stories)} items...")
        
        df = pd.DataFrame(all_stories)
        db = lancedb.connect("s3://sage-unified-feed-lance/lancedb/")
        
        try:
            db.drop_table("unified_feed")
            print("   🗑️  Dropped old table")
        except:
            pass
        
        table = db.create_table("unified_feed", df)
        
        # Count stats
        real_links = sum(1 for s in all_stories if any(domain in str(s.get('enriched_content', '')) for domain in ['bloomberg.com', 'businessinsider.com', 'reuters.com', 'weekendreads.cmail', 'barrons.cmail', 'estadao.com.br', 'folha']))
        newsbrief_stories = sum(1 for s in all_stories if '- Newsbrief' in str(s.get('sender_tag', '')))
        
        print(f"\n✅ DATABASE CREATED!")
        print(f"   • Total items: {len(all_stories)}")
        print(f"   • NewsBreif stories: {newsbrief_stories}")
        print(f"   • REAL article links: {real_links}")
        print(f"   • Link accuracy: {real_links/len(all_stories)*100:.1f}%")
        
        return len(all_stories)
    else:
        print("❌ No stories created")
        return 0

if __name__ == "__main__":
    count = fetch_and_process_emails(10)
    print(f"\n🎯 Complete! Created database with {count} items")
