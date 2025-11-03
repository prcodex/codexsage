#!/usr/bin/env python3
"""
SAGE Unified Pipeline Script
Complete 8-step process with multiple execution modes

Usage:
    python3 run_pipeline.py --fetch-new        # Fetch and process new emails
    python3 run_pipeline.py --reenrich --last 10   # Re-enrich latest 10
    python3 run_pipeline.py --enrich-unenriched    # Process backlog (for cron)
    python3 run_pipeline.py --recreate-db          # Fresh database rebuild
    python3 run_pipeline.py --enrich-id abc123     # Re-enrich specific email
"""

import argparse
import lancedb
import pandas as pd
import json
import os
import sys
import re
from datetime import datetime, timedelta
from anthropic import Anthropic

# Import our modules
from tag_to_rule_mapping import TAG_TO_RULE

# Handler definitions
NEWSBRIEF_HANDLERS = [
    'newsbrief',
    'newsbrief_portuguese',
    'newsbrief_portuguese_with_links'
]

def print_header(title):
    """Print formatted section header"""
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80 + "\n")

def print_step(step_num, step_name):
    """Print step header"""
    print(f"\n{'━' * 80}")
    print(f"STEP {step_num}: {step_name}")
    print(f"{'━' * 80}\n")

# ═══════════════════════════════════════════════════════════════════════════
# STEP 1: FETCH EMAILS FROM GMAIL
# ═══════════════════════════════════════════════════════════════════════════

def fetch_emails_from_gmail(hours_back=24):
    """
    Fetch emails from Gmail IMAP
    Returns list of raw email dictionaries
    """
    import imaplib
    import email
    from email.utils import parseaddr, parsedate_to_datetime
    from bs4 import BeautifulSoup
    import hashlib
    
    print("📥 Connecting to Gmail IMAP...")
    
    # Get credentials
    gmail_user = os.getenv('GMAIL_USER', 'YOUR_EMAIL@gmail.com')
    gmail_pwd = os.getenv('GMAIL_APP_PASSWORD', os.getenv('GMAIL_APP_PASSWORD'))
    
    # Connect
    mail = imaplib.IMAP4_SSL('imap.gmail.com', 993)
    mail.login(gmail_user, gmail_pwd)
    mail.select('INBOX')
    
    # Search for recent emails
    since_date = (datetime.now() - timedelta(hours=hours_back)).strftime("%d-%b-%Y")
    status, messages = mail.search(None, f'(SINCE "{since_date}")')
    
    email_ids = messages[0].split()
    print(f"   Found {len(email_ids)} emails from last {hours_back} hours")
    
    emails = []
    for msg_id in email_ids[-50:]:  # Limit to last 50
        try:
            status, data = mail.fetch(msg_id, '(RFC822)')
            email_message = email.message_from_bytes(data[0][1])
            
            # Extract fields
            subject = email_message.get('Subject', '')
            from_addr = parseaddr(email_message.get('From', ''))[1]
            date = parsedate_to_datetime(email_message.get('Date'))
            
            # Extract HTML content
            html_content = ''
            text_content = ''
            
            if email_message.is_multipart():
                for part in email_message.walk():
                    if part.get_content_type() == 'text/html':
                        html_content = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                    elif part.get_content_type() == 'text/plain':
                        text_content = part.get_payload(decode=True).decode('utf-8', errors='ignore')
            else:
                content = email_message.get_payload(decode=True).decode('utf-8', errors='ignore')
                if email_message.get_content_type() == 'text/html':
                    html_content = content
                else:
                    text_content = content
            
            # Generate unique ID
            unique_str = f"{subject}{from_addr}{date.isoformat()}"
            email_id = hashlib.md5(unique_str.encode()).hexdigest()
            
            emails.append({
                'id': email_id,
                'subject': subject,
                'sender': from_addr,
                'date': date.isoformat(),
                'content_html': html_content,
                'content_text': text_content or html_content
            })
            
        except Exception as e:
            print(f"   ⚠️  Error fetching email: {e}")
            continue
    
    mail.logout()
    print(f"✅ Fetched {len(emails)} emails successfully")
    return emails

# ═══════════════════════════════════════════════════════════════════════════
# STEP 2: FILTER BY ALLOWED SENDERS
# ═══════════════════════════════════════════════════════════════════════════

def filter_allowed_senders(emails, allowed_senders):
    """
    Filter emails to only allowed senders
    Returns filtered list with initial sender_tag
    """
    print(f"🔍 Filtering {len(emails)} emails against allowed senders...")
    
    filtered = []
    for email in emails:
        sender = email['sender'].lower()
        
        # Check each sender group
        for sender_group in allowed_senders:
            if not sender_group.get('active', True):
                continue
            
            # Check each pattern
            for pattern in sender_group['email_patterns']:
                if pattern.lower() in sender:
                    email['initial_sender_tag'] = sender_group['sender_tag']
                    filtered.append(email)
                    break
            
            if email.get('initial_sender_tag'):
                break
    
    print(f"✅ Allowed: {len(filtered)}, Blocked: {len(emails) - len(filtered)}")
    return filtered

# ═══════════════════════════════════════════════════════════════════════════
# STEP 3: DETECT SENDER TAG
# ═══════════════════════════════════════════════════════════════════════════

def detect_sender_tag(email, detection_rules):
    """
    Apply detection rules to assign final sender_tag
    Returns sender_tag string
    """
    sender_tag = email.get('initial_sender_tag', '')
    subject = email.get('subject', '').lower()
    body = email.get('content_text', '').lower()
    
    # Check each rule
    for rule_name, rule in detection_rules.items():
        # Check sender match
        sender_match = (rule.get('sender', '') == email.get('initial_sender_tag', ''))
        
        # Check subject match
        subject_pattern = rule.get('subject_contains', '')
        subject_match = (not subject_pattern) or (subject_pattern.lower() in subject)
        
        # Check body match
        body_pattern = rule.get('body_contains', '')
        body_match = (not body_pattern) or (body_pattern.lower() in body)
        
        # Apply logic
        logic = rule.get('logic', 'AND')
        
        if logic == 'AND':
            if sender_match and subject_match and body_match:
                return rule_name
        elif logic == 'OR':
            if sender_match or subject_match or body_match:
                return rule_name
    
    # No specific rule matched - use initial tag
    return sender_tag

# ═══════════════════════════════════════════════════════════════════════════
# STEP 4: STORE TO DATABASE
# ═══════════════════════════════════════════════════════════════════════════

def store_to_database(emails):
    """
    Store raw emails to LanceDB
    Returns number of emails stored
    """
    print(f"💾 Storing {len(emails)} emails to database...")
    
    db = lancedb.connect('s3://sage-unified-feed-lance/lancedb/')
    
    # Open or create table
    try:
        table = db.open_table('unified_feed')
    except:
        # Create table if doesn't exist
        df = pd.DataFrame(emails)
        table = db.create_table('unified_feed', df)
        print("✅ Created new table")
        return len(emails)
    
    # Check for duplicates and add new ones
    stored = 0
    for email in emails:
        existing = table.search().where(f"id = '{email['id']}'").to_pandas()
        
        if existing.empty:
            # Create record with empty enrichment fields
            record = {
                'id': email['id'],
                'source_type': 'email',
                'created_at': email['date'],
                'sender_tag': email['sender_tag'],
                'title': email['subject'],
                'content_html': email['content_html'],
                'content_text': email['content_text'],
                'enriched_content': '',
                'actors': '',
                'themes': '',
                'ai_score': 0.0,
                'link': '',
                'custom_fields': '{}'
            }
            
            df = pd.DataFrame([record])
            table.add(df)
            stored += 1
    
    print(f"✅ Stored {stored} new emails")
    return stored

# ═══════════════════════════════════════════════════════════════════════════
# STEP 5-6: MAP & ENRICH
# ═══════════════════════════════════════════════════════════════════════════

def execute_handler(handler_name, title, content_text, content_html):
    """
    Execute the appropriate enrichment handler
    Returns enrichment result
    """
    # Import handlers dynamically
    if handler_name == 'newsbrief':
        from newsbrief_handler import enrich_newsbrief
        return enrich_newsbrief(title, content_text, content_html)
    
    elif handler_name == 'gold_standard':
        from gold_standard_enhanced_handler import enrich_gold_standard
        return enrich_gold_standard(title, content_text)
    
    elif handler_name == 'itau_daily':
        from itau_daily_handler import enrich_itau_daily
        return enrich_itau_daily(title, content_text)
    
    # Add more handlers as needed
    else:
        # Default handler
        return {
            'enriched_content': f'Rule: {handler_name}\n\n{content_text[:1000]}',
            'ai_score': 5.0
        }

# ═══════════════════════════════════════════════════════════════════════════
# STEP 7: EXTRACT KEYWORDS
# ═══════════════════════════════════════════════════════════════════════════

def extract_keywords(title, content):
    """
    Extract keywords using Option C hybrid approach
    """
    from keyword_extractor import extract_keywords as extract_kw
    return extract_kw(title, content)

# ═══════════════════════════════════════════════════════════════════════════
# NEWSBRIEF SPLITTING
# ═══════════════════════════════════════════════════════════════════════════

def split_newsbrief_enrichment(enrichment_text, original_email):
    """
    Parse NewsBreif enrichment into individual stories
    """
    from smart_link_matcher import match_story_to_link
    
    stories = []
    
    # Find all numbered stories
    pattern = r'<strong[^>]*>(\d+)\.\s+([^<]+)</strong>(.*?)(?=<strong|$)'
    matches = re.findall(pattern, enrichment_text, re.DOTALL)
    
    for number, title, content in matches:
        story = {
            'number': number,
            'title': f"{number}. {title.strip()}",
            'content': content.strip(),
            'original_email_html': original_email.get('content_html', ''),
            'original_email_id': original_email.get('id', ''),
            'created_at': original_email.get('created_at', '')
        }
        
        # Match link for this story
        if original_email.get('content_html'):
            link = match_story_to_link(story['title'], original_email['content_html'])
            story['link'] = link if link else ''
        else:
            story['link'] = ''
        
        stories.append(story)
    
    return stories

# ═══════════════════════════════════════════════════════════════════════════
# PIPELINE MODES
# ═══════════════════════════════════════════════════════════════════════════

def mode_fetch_new():
    """
    Mode: Fetch new emails from Gmail and process completely (Steps 1-8)
    """
    print_header("MODE: FETCH NEW EMAILS (Complete Pipeline)")
    
    # STEP 1: Fetch
    print_step(1, "FETCH from Gmail")
    emails = fetch_emails_from_gmail(hours_back=24)
    
    if not emails:
        print("No emails fetched")
        return
    
    # STEP 2: Filter
    print_step(2, "FILTER by allowed senders")
    with open('allowed_senders.json', 'r') as f:
        allowed_senders = json.load(f)
    filtered = filter_allowed_senders(emails, allowed_senders)
    
    if not filtered:
        print("No allowed emails")
        return
    
    # STEP 3: Tag
    print_step(3, "DETECT sender tags")
    with open('tag_detection_rules.json', 'r') as f:
        detection_rules = json.load(f)
    
    for email in filtered:
        tag = detect_sender_tag(email, detection_rules)
        email['sender_tag'] = tag
        print(f"   {email['subject'][:50]}... → {tag}")
    
    # STEP 4: Store
    print_step(4, "STORE to database")
    stored = store_to_database(filtered)
    
    # STEPS 5-8: Enrich the newly stored emails
    print_step("5-8", "ENRICH newly stored emails")
    enrich_emails(email_ids=[e['id'] for e in filtered])

def mode_reenrich_last(n):
    """
    Mode: Re-enrich latest N emails (Steps 5-8 only)
    """
    print_header(f"MODE: RE-ENRICH LATEST {n} EMAILS")
    
    # Get latest N emails
    db = lancedb.connect('s3://sage-unified-feed-lance/lancedb/')
    table = db.open_table('unified_feed')
    df = table.to_pandas()
    
    # Sort by date, get latest N
    df['created_at'] = pd.to_datetime(df['created_at'])
    df = df.sort_values('created_at', ascending=False)
    latest = df.head(n)
    
    print(f"Selected {len(latest)} latest emails for re-enrichment")
    
    # For NewsBreif emails that were split, delete old stories first
    for idx, email in latest.iterrows():
        email_id = email['id']
        tag = email['sender_tag']
        handler = TAG_TO_RULE.get(tag, 'classification')
        
        if handler in NEWSBRIEF_HANDLERS:
            # Delete old split stories
            print(f"   🗑️  Deleting old stories for {email_id}...")
            df_updated = df[~df['id'].str.startswith(f"{email_id}_story_")]
            df = df_updated
    
    # Update table
    table.delete("id IS NOT NULL")
    table.add(df)
    
    # Now enrich
    email_ids = latest['id'].tolist()
    enrich_emails(email_ids=email_ids)

def mode_enrich_unenriched():
    """
    Mode: Enrich all unenriched emails (Steps 5-8, for cron)
    """
    print_header("MODE: ENRICH UNENRICHED EMAILS (Backlog Processing)")
    
    # Get unenriched emails
    db = lancedb.connect('s3://sage-unified-feed-lance/lancedb/')
    table = db.open_table('unified_feed')
    df = table.to_pandas()
    
    unenriched = df[
        (df['enriched_content'].isna()) | 
        (df['enriched_content'] == '') |
        (df['enriched_content'] == 'SPLIT_INTO_STORIES')
    ]
    
    print(f"Found {len(unenriched)} unenriched emails")
    
    if len(unenriched) == 0:
        print("✅ No emails to enrich")
        return
    
    email_ids = unenriched['id'].tolist()
    enrich_emails(email_ids=email_ids)

def mode_recreate_database():
    """
    Mode: Recreate database from scratch (fetch 10-15 recent emails)
    """
    print_header("MODE: RECREATE DATABASE")
    
    # Drop existing table
    print("🗑️  Dropping existing table...")
    db = lancedb.connect('s3://sage-unified-feed-lance/lancedb/')
    try:
        db.drop_table('unified_feed')
        print("   ✅ Table dropped")
    except:
        print("   ℹ️  No existing table")
    
    # Fetch recent emails
    print("\n📥 Fetching last 10-15 emails from Gmail...")
    emails = fetch_emails_from_gmail(hours_back=72)  # Last 3 days
    
    if not emails:
        print("❌ No emails fetched")
        return
    
    # Filter
    print("\n🔍 Filtering by allowed senders...")
    with open('allowed_senders.json', 'r') as f:
        allowed_senders = json.load(f)
    filtered = filter_allowed_senders(emails, allowed_senders)
    
    # Limit to 15 most recent
    filtered = filtered[-15:]
    print(f"   Selected {len(filtered)} most recent allowed emails")
    
    # Tag
    print("\n🏷️  Detecting sender tags...")
    with open('tag_detection_rules.json', 'r') as f:
        detection_rules = json.load(f)
    
    for email in filtered:
        tag = detect_sender_tag(email, detection_rules)
        email['sender_tag'] = tag
    
    # Create table and store
    print("\n💾 Creating new database table...")
    records = []
    for email in filtered:
        records.append({
            'id': email['id'],
            'source_type': 'email',
            'created_at': email['date'],
            'sender_tag': email['sender_tag'],
            'title': email['subject'],
            'content_html': email['content_html'],
            'content_text': email['content_text'],
            'enriched_content': '',
            'actors': '',
            'themes': '',
            'ai_score': 0.0,
            'link': '',
            'custom_fields': '{}'
        })
    
    df = pd.DataFrame(records)
    table = db.create_table('unified_feed', df, mode='overwrite')
    print(f"✅ Created table with {len(records)} emails")
    
    # Enrich all
    print("\n🤖 Enriching all emails...")
    email_ids = [e['id'] for e in filtered]
    enrich_emails(email_ids=email_ids)

# ═══════════════════════════════════════════════════════════════════════════
# CORE ENRICHMENT FUNCTION (Steps 5-8)
# ═══════════════════════════════════════════════════════════════════════════

def enrich_emails(email_ids=None):
    """
    Core enrichment function: Steps 5-8
    Handles both regular and NewsBreif emails
    """
    db = lancedb.connect('s3://sage-unified-feed-lance/lancedb/')
    table = db.open_table('unified_feed')
    df = table.to_pandas()
    
    # Filter to specified IDs
    if email_ids:
        df_to_enrich = df[df['id'].isin(email_ids)]
    else:
        # All unenriched
        df_to_enrich = df[
            (df['enriched_content'].isna()) | 
            (df['enriched_content'] == '')
        ]
    
    print(f"\n📊 Enriching {len(df_to_enrich)} emails...")
    
    enriched_count = 0
    
    for idx, email in df_to_enrich.iterrows():
        email_id = email['id']
        tag = email['sender_tag']
        title = email['title']
        
        print(f"\n📧 Email: {title[:60]}...")
        
        # STEP 5: Map to handler
        handler = TAG_TO_RULE.get(tag, 'classification')
        print(f"   Tag: {tag} → Handler: {handler}")
        
        # STEP 6: Run enrichment
        print(f"   🤖 Running {handler} handler...")
        try:
            enrichment = execute_handler(
                handler,
                email['title'],
                email['content_text'],
                email['content_html']
            )
        except Exception as e:
            print(f"   ❌ Error: {e}")
            continue
        
        print(f"   ✅ Enrichment: {len(enrichment.get('enriched_content', ''))} chars")
        
        # DECISION: NewsBreif or regular?
        if handler in NEWSBRIEF_HANDLERS:
            
            # ═══════════════════════════════════════
            # NEWSBRIEF PATH (Create multiple entries)
            # ═══════════════════════════════════════
            
            print(f"   📰 NewsBreif detected - splitting stories...")
            
            stories = split_newsbrief_enrichment(
                enrichment['enriched_content'],
                email.to_dict()
            )
            
            print(f"   Found {len(stories)} stories")
            
            for i, story in enumerate(stories):
                # STEP 7: Keywords for THIS story
                print(f"   🔑 Story {i+1}: Extracting keywords...")
                keywords = extract_keywords(story['title'], story['content'])
                
                # STEP 8: CREATE new database entry
                new_entry = {
                    'id': f"{email_id}_story_{i}",
                    'source_type': 'email',
                    'created_at': story['created_at'],
                    'sender_tag': f"{tag}- Newsbrief",
                    'title': story['title'],
                    'content_html': story['original_email_html'],
                    'content_text': story['content'],
                    'enriched_content': story['content'],
                    'actors': keywords,
                    'themes': '',
                    'ai_score': 8.0,
                    'link': story.get('link', ''),
                    'custom_fields': '{}'
                }
                
                table.add(pd.DataFrame([new_entry]))
                print(f"   ✅ Saved story {i+1}: {keywords}")
            
            # Mark original as processed
            df.loc[idx, 'enriched_content'] = 'SPLIT_INTO_STORIES'
            df.loc[idx, 'actors'] = f'Split into {len(stories)} stories'
            
            enriched_count += len(stories)
        
        else:
            
            # ═══════════════════════════════════════
            # REGULAR PATH (Update existing entry)
            # ═══════════════════════════════════════
            
            # STEP 7: Keywords for whole email
            print(f"   🔑 Extracting keywords...")
            keywords = extract_keywords(title, enrichment['enriched_content'])
            
            # STEP 8: UPDATE database entry
            df.loc[idx, 'enriched_content'] = enrichment['enriched_content']
            df.loc[idx, 'actors'] = keywords
            df.loc[idx, 'ai_score'] = enrichment.get('ai_score', 0.0)
            
            print(f"   ✅ Keywords: {keywords}")
            enriched_count += 1
    
    # Save updates to database
    print(f"\n💾 Saving updates to database...")
    table.delete("id IS NOT NULL")
    table.add(df)
    
    print(f"\n✅ Enrichment complete: {enriched_count} entries created/updated")

# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description='SAGE Unified Pipeline')
    
    # Modes
    parser.add_argument('--fetch-new', action='store_true',
                       help='Fetch new emails from Gmail and process completely (Steps 1-8)')
    parser.add_argument('--reenrich', action='store_true',
                       help='Re-enrich existing emails (use with --last N)')
    parser.add_argument('--enrich-unenriched', action='store_true',
                       help='Enrich all unenriched emails (for cron)')
    parser.add_argument('--recreate-db', action='store_true',
                       help='Recreate database from scratch (fetch 10-15 recent)')
    parser.add_argument('--enrich-id', type=str,
                       help='Re-enrich specific email by ID')
    
    # Options
    parser.add_argument('--last', type=int,
                       help='Number of latest emails to process (use with --reenrich)')
    
    args = parser.parse_args()
    
    # Check for API key
    if not os.getenv('ANTHROPIC_API_KEY'):
        print("❌ Error: ANTHROPIC_API_KEY not set")
        print("   Run: export ANTHROPIC_API_KEY='your-key-here'")
        sys.exit(1)
    
    # Execute mode
    if args.fetch_new:
        mode_fetch_new()
    
    elif args.reenrich:
        if not args.last:
            print("❌ Error: --reenrich requires --last N")
            sys.exit(1)
        mode_reenrich_last(args.last)
    
    elif args.enrich_unenriched:
        mode_enrich_unenriched()
    
    elif args.recreate_db:
        mode_recreate_database()
    
    elif args.enrich_id:
        enrich_emails(email_ids=[args.enrich_id])
    
    else:
        parser.print_help()
        print("\n💡 Examples:")
        print("   python3 run_pipeline.py --fetch-new")
        print("   python3 run_pipeline.py --reenrich --last 10")
        print("   python3 run_pipeline.py --enrich-unenriched")
        print("   python3 run_pipeline.py --recreate-db")

if __name__ == '__main__':
    main()
