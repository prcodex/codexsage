# Two-Stage Cron Architecture

**Complete automation strategy for SAGE email processing**

---

## Philosophy

**Separate fast operations (fetch) from slow operations (AI enrichment) for:**
- ✅ Reliability - If enrichment fails, fetch still works
- ✅ Speed - See raw emails immediately  
- ✅ Flexibility - Enrich old emails without re-fetching
- ✅ Scalability - Each stage can be optimized independently

---

## The Two-Stage Design

```
┌─────────────────────────────────────┐
│   STAGE 1: Fetch & Store            │
│   Every 30 minutes                  │
│   Duration: 1-2 minutes             │
│   Steps: 1-4                        │
├─────────────────────────────────────┤
│ • Fetch from Gmail IMAP             │
│ • Filter allowed senders            │
│ • Detect sender tags                │
│ • Store raw to LanceDB              │
└────────────┬────────────────────────┘
             ↓
       [LanceDB S3]
       Raw emails
       waiting for
       enrichment
             ↓
┌─────────────────────────────────────┐
│   STAGE 2: Enrich Complete          │
│   Every 15 minutes                  │
│   Duration: 5-10 minutes            │
│   Steps: 5-8 + NewsBreif Split      │
├─────────────────────────────────────┤
│ • Map tag to handler                │
│ • Run enrichment handler            │
│ • IF NewsBreif: Split stories       │
│ • Extract keywords (per entry)      │
│ • Save enrichment                   │
└────────────┬────────────────────────┘
             ↓
       [LanceDB S3]
       Enriched emails
       ready for display
             ↓
      Display (8540)
```

---

## Stage 1: Fetch & Store

### Cron Schedule
```bash
# Runs at :00 and :30 every hour
0,30 * * * * /home/ubuntu/newspaper_project/cron/fetch_and_store.sh >> /home/ubuntu/logs/fetch.log 2>&1
```

### Script: fetch_and_store.sh
```bash
#!/bin/bash
#
# SAGE Cron Stage 1: Fetch & Store
# Fetches emails from Gmail and stores them raw in database
#

cd /home/ubuntu/newspaper_project

# Load environment
source gmail_env.sh

# Run fetch & store (Steps 1-4)
python3 fetch_and_store.py

exit 0
```

### Script: fetch_and_store.py
```python
#!/usr/bin/env python3
"""
SAGE Stage 1: Fetch & Store
Steps 1-4: Gmail → Filter → Tag → Store
"""

import lancedb
import pandas as pd
from sage4_gmail_robust import fetch_emails_from_gmail
from tag_detection import detect_sender_tag
import json

def main():
    print("=" * 80)
    print("SAGE STAGE 1: FETCH & STORE")
    print("=" * 80)
    
    # STEP 1: Fetch from Gmail
    print("\n📥 Step 1: Fetching from Gmail...")
    raw_emails = fetch_emails_from_gmail(hours_back=1)  # Last hour
    print(f"   Fetched {len(raw_emails)} emails")
    
    # STEP 2: Filter by allowed senders
    print("\n🔍 Step 2: Filtering allowed senders...")
    with open('allowed_senders.json', 'r') as f:
        allowed_senders = json.load(f)
    
    filtered = filter_allowed_senders(raw_emails, allowed_senders)
    print(f"   Allowed: {len(filtered)}, Blocked: {len(raw_emails) - len(filtered)}")
    
    # STEP 3: Detect sender tags
    print("\n🏷️  Step 3: Detecting sender tags...")
    with open('tag_detection_rules.json', 'r') as f:
        detection_rules = json.load(f)
    
    for email in filtered:
        tag = detect_sender_tag(email, detection_rules)
        email['sender_tag'] = tag
        print(f"   {email['subject'][:50]}... → {tag}")
    
    # STEP 4: Store to database
    print("\n💾 Step 4: Storing to database...")
    db = lancedb.connect('s3://sage-unified-feed-lance/lancedb/')
    table = db.open_table('unified_feed')
    
    stored = 0
    for email in filtered:
        # Check for duplicates
        existing = table.search().where(f"id = '{email['id']}'").to_pandas()
        if not existing.empty:
            continue
        
        # Create record
        record = {
            'id': email['id'],
            'source_type': 'email',
            'created_at': email['date'],
            'sender_tag': email['sender_tag'],
            'title': email['subject'],
            'content_html': email['content_html'],
            'content_text': email['content_text'],
            'enriched_content': '',  # Empty - filled in Stage 2
            'actors': '',  # Empty - filled in Stage 2
            'themes': '',
            'ai_score': 0.0,
            'link': '',
            'custom_fields': '{}'
        }
        
        df = pd.DataFrame([record])
        table.add(df)
        stored += 1
    
    print(f"   Stored {stored} new emails")
    print("\n✅ STAGE 1 COMPLETE")
    print("=" * 80)

if __name__ == '__main__':
    main()
```

### Duration
**1-2 minutes** (no AI calls, just Gmail IMAP and database writes)

### Output
Raw emails in database with `sender_tag`, ready for enrichment.

### Error Handling
```bash
# In fetch_and_store.sh
if [ $? -ne 0 ]; then
    echo "❌ Stage 1 failed, retrying in 5 minutes..."
    sleep 300
    python3 fetch_and_store.py
fi
```

---

## Stage 2: Enrich Complete

### Cron Schedule
```bash
# Runs every 15 minutes
*/15 * * * * /home/ubuntu/newspaper_project/cron/enrich_complete.sh >> /home/ubuntu/logs/enrich.log 2>&1
```

### Script: enrich_complete.sh
```bash
#!/bin/bash
#
# SAGE Cron Stage 2: Enrich Complete
# Enriches unenriched emails, handles NewsBreif splitting
#

cd /home/ubuntu/newspaper_project

# Load API key
export ANTHROPIC_API_KEY="YOUR_ANTHROPIC_API_KEY_HERE"

# Run enrichment (Steps 5-8 + NewsBreif splitting)
python3 enrich_complete.py

exit 0
```

### Script: enrich_complete.py
```python
#!/usr/bin/env python3
"""
SAGE Stage 2: Enrich Complete
Steps 5-8: Map → Enrich → Keywords → Save
Special: Handles NewsBreif splitting
"""

import lancedb
import pandas as pd
from unified_adaptive_enrichment import execute_handler
from keyword_extractor import extract_keywords
from smart_link_matcher import match_story_to_link
from tag_to_rule_mapping import TAG_TO_RULE
import re

# NewsBreif handlers that need splitting
NEWSBRIEF_HANDLERS = [
    'newsbrief',
    'newsbrief_portuguese',
    'newsbrief_portuguese_with_links'
]

def split_newsbrief_enrichment(enrichment_text, original_email):
    """Parse NewsBreif enrichment into individual stories"""
    stories = []
    
    # Find all numbered stories with large titles
    pattern = r'<strong[^>]*>(\d+)\.\s+([^<]+)</strong>(.*?)(?=<strong|$)'
    matches = re.findall(pattern, enrichment_text, re.DOTALL)
    
    for number, title, content in matches:
        stories.append({
            'number': number,
            'title': f"{number}. {title.strip()}",
            'content': content.strip()
        })
    
    return stories

def main():
    print("=" * 80)
    print("SAGE STAGE 2: ENRICH COMPLETE")
    print("=" * 80)
    
    # Connect to database
    db = lancedb.connect('s3://sage-unified-feed-lance/lancedb/')
    table = db.open_table('unified_feed')
    
    # Query unenriched emails
    df = table.to_pandas()
    unenriched = df[
        (df['enriched_content'].isna()) | 
        (df['enriched_content'] == '')
    ]
    
    print(f"\n📊 Found {len(unenriched)} unenriched emails\n")
    
    if len(unenriched) == 0:
        print("✅ No emails to enrich, exiting")
        return
    
    enriched_count = 0
    
    for idx, email in unenriched.iterrows():
        email_id = email['id']
        tag = email['sender_tag']
        title = email['title']
        
        # STEP 5: Map tag to handler
        handler = TAG_TO_RULE.get(tag, 'classification')
        print(f"\n📧 Email: {title[:60]}...")
        print(f"   Tag: {tag} → Handler: {handler}")
        
        # STEP 6: Run enrichment handler
        print(f"   🤖 Running {handler} handler...")
        enrichment = execute_handler(
            handler=handler,
            title=email['title'],
            content_text=email['content_text'],
            content_html=email['content_html']
        )
        
        # DECISION POINT: NewsBreif or regular?
        if handler in NEWSBRIEF_HANDLERS:
            
            # ═══════════════════════════════════════
            # NEWSBRIEF SPECIAL PROCESSING
            # ═══════════════════════════════════════
            
            print(f"   📰 NewsBreif detected - splitting stories...")
            
            # Split enrichment into individual stories
            stories = split_newsbrief_enrichment(
                enrichment['enriched_content'],
                email
            )
            
            print(f"   Found {len(stories)} stories")
            
            # Process EACH story as separate entry
            for i, story in enumerate(stories):
                # STEP 7: Extract keywords for THIS story
                print(f"   🔑 Story {i+1}: Extracting keywords...")
                keywords = extract_keywords(story['title'], story['content'])
                
                # Match link for THIS story
                link = match_story_to_link(story['title'], email['content_html'])
                
                # STEP 8: CREATE new database entry
                new_entry = {
                    'id': f"{email_id}_story_{i}",
                    'source_type': 'email',
                    'created_at': email['created_at'],
                    'sender_tag': f"{tag}- Newsbrief",
                    'title': story['title'],
                    'content_html': email['content_html'],
                    'content_text': story['content'],
                    'enriched_content': story['content'],
                    'actors': keywords,
                    'themes': '',
                    'ai_score': 8.0,
                    'link': link or '',
                    'custom_fields': '{}'
                }
                
                # Add to database
                table.add(pd.DataFrame([new_entry]))
                print(f"   ✅ Saved story {i+1}: {keywords}")
            
            # Mark original as processed
            df.loc[idx, 'enriched_content'] = 'SPLIT_INTO_STORIES'
            df.loc[idx, 'actors'] = f'Split into {len(stories)} stories'
            
            enriched_count += len(stories)
        
        else:
            
            # ═══════════════════════════════════════
            # REGULAR HANDLER PROCESSING
            # ═══════════════════════════════════════
            
            # STEP 7: Extract keywords for whole email
            print(f"   🔑 Extracting keywords...")
            keywords = extract_keywords(title, enrichment['enriched_content'])
            
            # STEP 8: UPDATE existing database entry
            df.loc[idx, 'enriched_content'] = enrichment['enriched_content']
            df.loc[idx, 'actors'] = keywords
            df.loc[idx, 'ai_score'] = enrichment.get('ai_score', 0.0)
            
            print(f"   ✅ Enriched: {keywords}")
            enriched_count += 1
    
    # Save all updates
    table.delete("id IS NOT NULL")
    table.add(df)
    
    print("\n" + "=" * 80)
    print(f"✅ STAGE 2 COMPLETE: Processed {len(unenriched)} emails → {enriched_count} entries")
    print("=" * 80)

if __name__ == '__main__':
    main()
```

### Duration
**5-10 minutes** (depends on backlog, includes AI calls)

### Output
Fully enriched emails/stories ready for display.

### Error Handling
```python
# Skip problematic emails, continue with others
try:
    enrichment = execute_handler(handler, email)
except Exception as e:
    print(f"❌ Error enriching {email['id']}: {e}")
    continue  # Skip this email, process next
```

---

## NewsBreif Integration

### Where Splitting Happens

**Inside Stage 2 (enrich_complete.py):**

```python
# After Step 6 (enrichment), before Steps 7-8 (keywords & save)

if handler in NEWSBRIEF_HANDLERS:
    # Split into stories
    stories = split_newsbrief_enrichment(enrichment, email)
    
    # For EACH story: Extract keywords + Save
    for story in stories:
        keywords = extract_keywords(story)  # Step 7
        save_story_entry(story, keywords)    # Step 8
else:
    # Regular flow
    keywords = extract_keywords(email, enrichment)  # Step 7
    update_email_entry(email, enrichment, keywords)  # Step 8
```

### Why in Stage 2?
- ✅ Enrichment already done (has formatted stories)
- ✅ Can extract keywords per story (better quality)
- ✅ Can match links per story (better accuracy)
- ✅ No separate cron needed (integrated naturally)

### Alternative Considered: Separate Cron 3 for Splitting
**Rejected because:**
- ❌ More complexity (3 crons instead of 2)
- ❌ Coordination issues (when does it run?)
- ❌ Another failure point
- ❌ No real benefit over integrated approach

---

## Frequency Design

### Stage 1: Every 30 Minutes
```
:00 - Fetch
:30 - Fetch
```

**Rationale:**
- Most briefings arrive 2x per day (morning, evening)
- 30 min catches them within reasonable time
- Not too aggressive on Gmail API (rate limits)
- Fast execution allows frequent runs

### Stage 2: Every 15 Minutes
```
:00 - Enrich
:15 - Enrich
:30 - Enrich
:45 - Enrich
```

**Rationale:**
- Runs MORE often than fetch (catches up faster)
- If no unenriched emails: exits in <5 seconds
- If backlog exists: processes 20-30 emails per run
- NewsBreif splitting handled automatically

### Timeline Example

```
10:00 AM → Stage 1 runs
           ├→ Fetches 2 new emails
           ├→ Filters: 2 allowed, 0 blocked
           ├→ Tags: bloomberg×1, goldman_sachs×1
           └→ Stores 2 raw emails
           Duration: 1 min 23 sec

10:15 AM → Stage 2 runs
           ├→ Finds 2 unenriched emails
           ├→ Email 1 (bloomberg → newsbrief):
           │  ├→ Enrichment: 3,200 chars with 6 stories
           │  ├→ Splits into 6 individual stories
           │  ├→ Extracts keywords for each (6 AI calls)
           │  ├→ Matches links (4 real, 2 HTML popup)
           │  └→ Creates 6 database entries
           ├→ Email 2 (goldman_sachs → gold_standard):
           │  ├→ Enrichment: 4,100 chars
           │  ├→ Extracts keywords (1 AI call)
           │  └→ Updates database entry
           └→ Result: 7 new items on port 8540
           Duration: 8 min 47 sec

10:30 AM → Stage 1 runs
           └→ No new emails, duration: 47 sec

10:45 AM → Stage 2 runs
           └→ No unenriched emails, duration: 4 sec

11:00 AM → Stage 1 runs
           └→ Fetches 1 new email (Itau Daily)
           Duration: 52 sec

11:15 AM → Stage 2 runs
           ├→ Enriches Itau email (itau_daily handler)
           └→ Creates 1 enriched entry
           Duration: 3 min 12 sec
```

**Typical latency:** New email enriched within 15-45 minutes

---

## Logging Strategy

### Stage 1: Fetch Log
**Location:** `/home/ubuntu/logs/fetch.log`

**Format:**
```
[2025-11-03 10:00:00] ════════════════════════════════════════
[2025-11-03 10:00:00] SAGE STAGE 1: FETCH & STORE
[2025-11-03 10:00:00] ════════════════════════════════════════
[2025-11-03 10:00:01] 
[2025-11-03 10:00:01] 📥 Step 1: Fetching from Gmail...
[2025-11-03 10:00:15]    Fetched 2 emails
[2025-11-03 10:00:15] 
[2025-11-03 10:00:15] 🔍 Step 2: Filtering allowed senders...
[2025-11-03 10:00:16]    Allowed: 2, Blocked: 0
[2025-11-03 10:00:16] 
[2025-11-03 10:00:16] 🏷️  Step 3: Detecting sender tags...
[2025-11-03 10:00:16]    Morning Briefing: Markets Digest Fed Comments... → bloomberg
[2025-11-03 10:00:17]    Q4 Economic Outlook... → goldman_sachs
[2025-11-03 10:00:17] 
[2025-11-03 10:00:17] 💾 Step 4: Storing to database...
[2025-11-03 10:00:18]    Stored 2 new emails
[2025-11-03 10:00:18] 
[2025-11-03 10:00:18] ✅ STAGE 1 COMPLETE
[2025-11-03 10:00:18] ════════════════════════════════════════
```

### Stage 2: Enrich Log
**Location:** `/home/ubuntu/logs/enrich.log`

**Format:**
```
[2025-11-03 10:15:00] ════════════════════════════════════════
[2025-11-03 10:15:00] SAGE STAGE 2: ENRICH COMPLETE
[2025-11-03 10:15:00] ════════════════════════════════════════
[2025-11-03 10:15:01] 
[2025-11-03 10:15:01] 📊 Found 2 unenriched emails
[2025-11-03 10:15:01] 
[2025-11-03 10:15:02] 📧 Email: Morning Briefing: Markets Digest Fed Comments...
[2025-11-03 10:15:02]    Tag: bloomberg → Handler: newsbrief
[2025-11-03 10:15:03]    🤖 Running newsbrief handler...
[2025-11-03 10:15:15]    ✅ Enrichment complete (3,200 chars)
[2025-11-03 10:15:16]    📰 NewsBreif detected - splitting stories...
[2025-11-03 10:15:17]    Found 6 stories
[2025-11-03 10:15:18]    🔑 Story 1: Extracting keywords...
[2025-11-03 10:15:20]    ✅ Saved story 1: Fed • Jerome Powell • Dollar
[2025-11-03 10:15:21]    🔑 Story 2: Extracting keywords...
[2025-11-03 10:15:22]    ✅ Saved story 2: China • Trade War • Exports
[2025-11-03 10:15:23]    🔑 Story 3: Extracting keywords...
[2025-11-03 10:15:24]    ✅ Saved story 3: Tech Stocks • Nasdaq • AI Rally
[2025-11-03 10:15:25]    🔑 Story 4: Extracting keywords...
[2025-11-03 10:15:26]    ✅ Saved story 4: Oil • OPEC • Supply Cuts
[2025-11-03 10:15:27]    🔑 Story 5: Extracting keywords...
[2025-11-03 10:15:28]    ✅ Saved story 5: Inflation • CPI • Fed Policy
[2025-11-03 10:15:29]    🔑 Story 6: Extracting keywords...
[2025-11-03 10:15:30]    ✅ Saved story 6: Corporate Earnings • Q4 Results
[2025-11-03 10:15:31] 
[2025-11-03 10:15:31] 📧 Email: Q4 Economic Outlook...
[2025-11-03 10:15:31]    Tag: goldman_sachs → Handler: gold_standard
[2025-11-03 10:15:32]    🤖 Running gold_standard handler...
[2025-11-03 10:15:45]    ✅ Enrichment complete (4,100 chars)
[2025-11-03 10:15:46]    🔑 Extracting keywords...
[2025-11-03 10:15:48]    ✅ Enriched: Fed • Interest Rates • Goldman Sachs • Q4
[2025-11-03 10:15:48] 
[2025-11-03 10:15:48] ════════════════════════════════════════
[2025-11-03 10:15:48] ✅ STAGE 2 COMPLETE: Processed 2 emails → 7 entries
[2025-11-03 10:15:48] ════════════════════════════════════════
```

### Duration
- **No backlog:** <5 seconds (quick exit)
- **Small backlog (1-5 emails):** 3-8 minutes
- **Large backlog (20+ emails):** 15-30 minutes

### Output
Fully enriched entries in database, visible on port 8540.

### Error Handling
```python
# Continue processing even if one email fails
for email in unenriched:
    try:
        enrichment = execute_handler(handler, email)
        keywords = extract_keywords(email, enrichment)
        save_enrichment(email, enrichment, keywords)
    except Exception as e:
        print(f"❌ Error processing {email['id']}: {e}")
        # Log error but continue with next email
        continue
```

---

## Monitoring & Alerts

### Health Checks

**Stage 1 Health:**
```bash
# Check if fetch is running
if ! pgrep -f "fetch_and_store.py" > /dev/null; then
    # Check last log time
    if [ $(find /home/ubuntu/logs/fetch.log -mmin +60) ]; then
        echo "⚠️  Stage 1 hasn't run in 60 minutes!"
    fi
fi
```

**Stage 2 Health:**
```bash
# Check for backlog
backlog=$(python3 -c "
import lancedb
db = lancedb.connect('s3://sage-unified-feed-lance/lancedb/')
table = db.open_table('unified_feed')
df = table.to_pandas()
unenriched = df[(df['enriched_content'].isna()) | (df['enriched_content'] == '')]
print(len(unenriched))
")

if [ "$backlog" -gt 50 ]; then
    echo "⚠️  Large enrichment backlog: $backlog emails"
fi
```

### Log Rotation

```bash
# In crontab: Daily log rotation at 3 AM
0 3 * * * /home/ubuntu/newspaper_project/cron/rotate_logs.sh

# rotate_logs.sh
#!/bin/bash
cd /home/ubuntu/logs

# Keep last 7 days of logs
find . -name "*.log" -mtime +7 -delete

# Compress old logs
gzip fetch.log enrich.log
mv fetch.log.gz "fetch-$(date +%Y%m%d).log.gz"
mv enrich.log.gz "enrich-$(date +%Y%m%d).log.gz"

# Start fresh logs
touch fetch.log enrich.log
```

---

## Installation & Setup

### 1. Create Cron Scripts

```bash
cd /home/ubuntu/newspaper_project

# Create cron directory
mkdir -p cron

# Copy scripts from automation/cron/ (in this repo)
cp /path/to/codexsage/automation/cron/fetch_and_store.sh cron/
cp /path/to/codexsage/automation/cron/enrich_complete.sh cron/

# Make executable
chmod +x cron/*.sh
```

### 2. Create Python Scripts

```bash
# fetch_and_store.py and enrich_complete.py
# (Full code shown in sections above)
```

### 3. Setup Logging

```bash
mkdir -p /home/ubuntu/logs
touch /home/ubuntu/logs/fetch.log
touch /home/ubuntu/logs/enrich.log
```

### 4. Install Cron Jobs

```bash
crontab -e

# Add these lines:
# SAGE Stage 1: Fetch & Store (Steps 1-4)
0,30 * * * * /home/ubuntu/newspaper_project/cron/fetch_and_store.sh >> /home/ubuntu/logs/fetch.log 2>&1

# SAGE Stage 2: Enrich Complete (Steps 5-8 + NewsBreif)
*/15 * * * * /home/ubuntu/newspaper_project/cron/enrich_complete.sh >> /home/ubuntu/logs/enrich.log 2>&1

# Log rotation (daily at 3 AM)
0 3 * * * /home/ubuntu/newspaper_project/cron/rotate_logs.sh
```

### 5. Test Manually

```bash
# Test Stage 1
cd /home/ubuntu/newspaper_project
./cron/fetch_and_store.sh

# Check output
tail -f /home/ubuntu/logs/fetch.log

# Test Stage 2
./cron/enrich_complete.sh

# Check output
tail -f /home/ubuntu/logs/enrich.log
```

---

## Performance Optimization

### Stage 1 Optimizations
- Fetch only last 1 hour (not 24 hours) after initial setup
- Use IMAP IDLE for push notifications (advanced)
- Batch database writes (10 emails at once)

### Stage 2 Optimizations
- Process emails in parallel (multiprocessing)
- Cache handler modules (don't reload each time)
- Batch keyword extractions (send 5 at once to Claude)

---

## Comparison: Two-Stage vs Single-Stage

### Two-Stage (CHOSEN)

**Pros:**
- ✅ Fast fetch (1-2 min) independent of enrichment
- ✅ Enrichment can catch up without blocking fetch
- ✅ Can see raw emails immediately
- ✅ Separate error handling
- ✅ Each stage optimizable independently

**Cons:**
- ❌ Two cron jobs to maintain
- ❌ Need coordination (enrichment waits for fetch)

### Single-Stage (Alternative)

**Pros:**
- ✅ Simpler (one cron job)
- ✅ Guaranteed complete processing

**Cons:**
- ❌ Slow (must wait for AI calls)
- ❌ If enrichment fails, nothing works
- ❌ Fetch blocked while enriching
- ❌ Can't enrich backlog without re-fetching

### Decision
**Two-stage for production reliability.**

---

## Future Enhancements

### Potential Stage 3: Vector Embeddings
```bash
# Run once per day at 2 AM
0 2 * * * /home/ubuntu/newspaper_project/cron/generate_embeddings.sh
```
- Generate semantic embeddings for all emails
- Enable similarity search
- Low priority (not critical for basic operation)

### Potential: Real-Time Processing
- Use IMAP IDLE instead of polling
- Instant enrichment on email arrival
- More complex, but minimal latency

---

## Status

**Current:** Conceptual design (NOT YET IMPLEMENTED)

**To Implement:**
1. Create `fetch_and_store.py` (Steps 1-4)
2. Create `enrich_complete.py` (Steps 5-8 + NewsBreif)
3. Create cron shell scripts
4. Test manually
5. Install in crontab
6. Monitor logs

**Ready when you are!**

---

**This design provides a robust, scalable, maintainable automation architecture for SAGE.**
