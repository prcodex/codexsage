# The 8-Step Email Processing Pipeline

**Complete technical reference for SAGE email processing from Gmail to enriched display**

---

## Overview

SAGE processes emails through 8 distinct steps, transforming raw Gmail messages into enriched, categorized, keyword-tagged intelligence cards.

```
Gmail IMAP
    ↓
Step 1: FETCH    → Get emails
Step 2: FILTER   → Keep allowed senders only  
Step 3: TAG      → Assign sender tags
Step 4: STORE    → Persist to database
    ↓
Step 5: MAP      → Determine handler
Step 6: ENRICH   → Run AI enrichment
Step 7: KEYWORDS → Extract specific terms
Step 8: SAVE     → Persist enrichment
    ↓
Display (8540)
```

---

## Step 1: FETCH Emails from Gmail

### Purpose
Connect to Gmail via IMAP and retrieve new emails from inbox.

### File
`src/scripts/sage4_gmail_robust.py`

### Process

1. **Load Gmail Credentials**
   ```python
   GMAIL_USER = os.getenv('GMAIL_USER')          # your_email@gmail.com
   GMAIL_APP_PASSWORD = os.getenv('GMAIL_APP_PASSWORD')
   ```

2. **Connect to Gmail IMAP**
   ```python
   import imaplib
   
   mail = imaplib.IMAP4_SSL('imap.gmail.com', 993)
   mail.login(GMAIL_USER, GMAIL_APP_PASSWORD)
   mail.select('INBOX')
   ```

3. **Search for Recent Emails**
   ```python
   # Get emails from last 24 hours
   since_date = (datetime.now() - timedelta(days=1)).strftime("%d-%b-%Y")
   status, messages = mail.search(None, f'(SINCE "{since_date}")')
   ```

4. **Fetch Each Email**
   ```python
   for msg_id in email_ids:
       # Fetch full email
       status, data = mail.fetch(msg_id, '(RFC822)')
       
       # Parse email
       email_message = email.message_from_bytes(data[0][1])
       
       # Extract parts
       subject = email_message['Subject']
       from_addr = email.utils.parseaddr(email_message['From'])[1]
       date = email.utils.parsedate_to_datetime(email_message['Date'])
       
       # Get HTML content
       html_content = extract_html_from_multipart(email_message)
       text_content = extract_text_from_multipart(email_message)
   ```

5. **Create Email Record**
   ```python
   email_record = {
       'id': generate_unique_id(subject, from_addr, date),
       'subject': subject,
       'sender': from_addr,
       'sender_name': extract_sender_name(from_addr),
       'date': date.isoformat(),
       'content_html': html_content,
       'content_text': text_content
   }
   ```

### Output
List of raw email dictionaries ready for filtering.

### Technical Notes
- Uses `imaplib` for Gmail connection
- Handles multipart emails (HTML + plain text)
- Extracts embedded images (CID references)
- Generates unique IDs via hash(subject + sender + date)
- Converts all dates to UTC ISO format

---

## Step 2: FILTER by Allowed Senders

### Purpose
Only process emails from pre-approved premium sources.

### File
`config/allowed_senders.json`

### Process

1. **Load Allowed Senders**
   ```python
   with open('config/allowed_senders.json', 'r') as f:
       allowed_senders = json.load(f)
   # Returns: List of 22 sender group objects
   ```

2. **For Each Fetched Email**
   ```python
   sender_email = email['sender']  # "jan.hatzius@gs.com"
   domain = sender_email.split('@')[1]  # "gs.com"
   ```

3. **Check Against Allowed Patterns**
   ```python
   def is_allowed(sender_email, allowed_senders):
       for sender_group in allowed_senders:
           if not sender_group['active']:
               continue
               
           for pattern in sender_group['email_patterns']:
               # Domain match: "gs.com" matches any "@gs.com"
               if pattern in sender_email:
                   return True, sender_group['sender_tag']
                   
               # Exact match: "janhatzius@gs.com"
               if pattern == sender_email:
                   return True, sender_group['sender_tag']
       
       return False, None
   ```

4. **Filter Results**
   ```python
   filtered_emails = []
   for email in fetched_emails:
       allowed, sender_tag = is_allowed(email['sender'], allowed_senders)
       if allowed:
           email['initial_sender_tag'] = sender_tag
           filtered_emails.append(email)
       else:
           log_blocked(email['sender'])
   ```

### Configuration Structure
```json
[
  {
    "sender_tag": "Goldman Sachs",
    "email_patterns": [
      "goldmansachs.com",
      "gs.com",
      "janhatzius@gs.com"
    ],
    "description": "Investment bank research and economic analysis",
    "active": true
  }
]
```

### Output
Filtered list of emails (only from allowed senders).

### Matching Logic
- **Domain-based:** "bloomberg.com" matches any user@bloomberg.com
- **Specific emails:** "janhatzius@gs.com" matches exact address
- **Case-insensitive:** "Bloomberg.com" = "bloomberg.com"
- **Active flag:** Can disable sender groups without deleting

---

## Step 3: DETECT and Assign Sender Tag

### Purpose
Assign specific routing tag based on email content patterns.

### File
`config/tag_detection_rules.json`

### Process

1. **Load Detection Rules**
   ```python
   with open('config/tag_detection_rules.json', 'r') as f:
       detection_rules = json.load(f)
   # Returns: Dictionary of 16 tagging rules
   ```

2. **For Each Allowed Email**
   ```python
   for email in filtered_emails:
       sender_tag = email['initial_sender_tag']
       subject = email['subject'].lower()
       body = email['content_text'].lower()
   ```

3. **Apply Detection Rules (First Match Wins)**
   ```python
   def detect_tag(email, rules):
       for rule_name, rule in rules.items():
           # Check sender match
           sender_match = (rule['sender'] == email['initial_sender_tag'])
           
           # Check subject match (if specified)
           subject_match = True
           if rule['subject_contains']:
               subject_match = rule['subject_contains'].lower() in email['subject'].lower()
           
           # Check body match (if specified)
           body_match = True
           if rule['body_contains']:
               body_match = rule['body_contains'].lower() in email['content_text'].lower()
           
           # Apply logic
           if rule['logic'] == 'AND':
               if sender_match and subject_match and body_match:
                   return rule_name
           elif rule['logic'] == 'OR':
               if sender_match or subject_match or body_match:
                   return rule_name
       
       # No specific rule matched - use initial tag
       return email['initial_sender_tag']
   ```

4. **Assign Final Tag**
   ```python
   final_tag = detect_tag(email, detection_rules)
   email['sender_tag'] = final_tag
   ```

### Configuration Structure
```json
{
  "WSJ Opinion": {
    "sender": "Wall Street Journal",
    "subject_contains": "Opinion:",
    "body_contains": "",
    "logic": "AND",
    "description": "WSJ Opinion articles - subject must contain 'Opinion:'"
  },
  "Rosenberg_EM": {
    "sender": "Rosenberg Research",
    "subject_contains": "Early Morning with Dave",
    "body_contains": "Fundamental Recommendations",
    "logic": "OR",
    "description": "Deep research - subject OR body match triggers"
  }
}
```

### Logic Types

**AND Logic:** ALL conditions must match
```
Sender = "Wall Street Journal" AND
Subject contains "Opinion:" AND
Body contains "" (empty = ignore)
→ Result: ALL filled conditions must be true
```

**OR Logic:** ANY condition can match
```
Sender = "Rosenberg Research" OR
Subject contains "Early Morning" OR
Body contains "Fundamental"
→ Result: If ANY condition is true, tag applies
```

### Output
Email with final `sender_tag` assigned for handler routing.

### Priority
Rules are checked in order. First matching rule wins. Put more specific rules before general ones.

---

## Step 4: STORE Raw Email to Database

### Purpose
Persist email data to LanceDB for future enrichment and reference.

### Database
LanceDB on S3: `s3://sage-unified-feed-lance/lancedb/unified_feed`

### Process

1. **Connect to LanceDB**
   ```python
   import lancedb
   import os
   
   os.environ['AWS_REGION'] = 'us-west-2'
   db = lancedb.connect('s3://sage-unified-feed-lance/lancedb/')
   ```

2. **Check for Existing Table**
   ```python
   if 'unified_feed' in db.table_names():
       table = db.open_table('unified_feed')
   else:
       # Create new table with schema
       table = db.create_table('unified_feed', data=initial_df)
   ```

3. **Create Database Record**
   ```python
   import pandas as pd
   from datetime import datetime
   
   record = {
       'id': email['id'],
       'source_type': 'email',
       'created_at': email['date'],  # ISO format string
       'sender_tag': email['sender_tag'],
       'title': email['subject'],
       'content_html': email['content_html'],
       'content_text': email['content_text'],
       
       # Empty fields - filled during enrichment
       'enriched_content': '',
       'actors': '',
       'themes': '',
       'ai_score': 0.0,
       'link': '',
       
       'custom_fields': '{}'
   }
   
   df = pd.DataFrame([record])
   ```

4. **Check for Duplicates**
   ```python
   existing = table.search().where(f"id = '{record['id']}'").to_pandas()
   
   if not existing.empty:
       print(f"Skipping duplicate: {record['id']}")
       continue
   ```

5. **Add to Database**
   ```python
   table.add(df)
   print(f"Stored email: {record['title']}")
   ```

### Database Schema

| Field | Type | Purpose | Filled In |
|-------|------|---------|-----------|
| id | string | Unique identifier | Step 1 |
| source_type | string | 'email' or 'tweet' | Step 1 |
| created_at | string | ISO datetime | Step 1 |
| sender_tag | string | Routing tag | Step 3 |
| title | string | Email subject | Step 1 |
| content_html | string | Full HTML body | Step 1 |
| content_text | string | Plain text body | Step 1 |
| enriched_content | string | AI summary | Step 6 |
| actors | string | Keywords | Step 7 |
| themes | string | Categories | Step 6 (optional) |
| ai_score | float | Relevance 0-10 | Step 6 (optional) |
| link | string | Article URL | Step 6 (if extracted) |
| custom_fields | string | JSON for extras | Any step |

### Output
Emails persisted to S3-backed LanceDB, ready for enrichment.

### Technical Notes
- S3 provides durable, scalable storage
- LanceDB optimized for vector operations
- ISO 8601 datetime format for consistency
- Idempotent: duplicate IDs are skipped
- Custom fields allow future expansion without schema changes

---

## Step 5: MAP Tag to Enrichment Handler

### Purpose
Determine which AI enrichment handler to use based on sender tag.

### File
`src/main/tag_to_rule_mapping.py`

### Process

1. **Load Tag Mappings**
   ```python
   from tag_to_rule_mapping import TAG_TO_RULE
   
   # Dictionary with 41 tag → handler mappings
   ```

2. **Query Unenriched Emails**
   ```python
   db = lancedb.connect('s3://sage-unified-feed-lance/lancedb/')
   table = db.open_table('unified_feed')
   
   # Get emails without enrichment
   df = table.to_pandas()
   unenriched = df[
       (df['enriched_content'].isna()) | 
       (df['enriched_content'] == '')
   ]
   ```

3. **Map Each Email to Handler**
   ```python
   for _, email in unenriched.iterrows():
       tag = email['sender_tag']
       
       # Look up handler
       handler = TAG_TO_RULE.get(tag, 'classification')
       
       print(f"Email: {email['title']}")
       print(f"Tag: {tag} → Handler: {handler}")
   ```

### Mapping Structure
```python
TAG_TO_RULE = {
    # Bloomberg variants
    'bloomberg': 'newsbrief',
    'bloomberg_breaking': 'bloomberg_breaking_news',
    
    # WSJ variants
    'wsj': 'newsbrief',
    'wsj_opinion': 'wsj_opinion_teaser',
    
    # Goldman Sachs
    'goldman_sachs': 'gold_standard',
    'goldman': 'gold_standard',
    'gs': 'gold_standard',
    
    # Rosenberg Research
    'rosenberg': 'rosenberg_deep_research',
    'rosenberg_research': 'breakfast_headlines',
    
    # Itau
    'itau': 'itau_daily',
    'itau_daily': 'itau_daily',
    
    # Portuguese sources
    'estadao': 'newsbrief_portuguese_with_links',
    'folha': 'newsbrief_portuguese',
    
    # Special handlers
    'cochrane': 'cochrane_detailed_summary',
    'javier_blas': 'javier_blas_special',
    
    # ... 41 total mappings
}
```

### Handler Types

| Handler | Used For | Output Style | Model | Cost |
|---------|----------|--------------|-------|------|
| newsbrief | Digests | Numbered stories | Sonnet | $0.015 |
| gold_standard | Research | Deep analysis | Sonnet | $0.024 |
| itau_daily | Itau bank | Bilingual summary | Sonnet | $0.015 |
| wsj_opinion_teaser | Opinion alerts | Title only | None | $0.000 |
| rosenberg_deep_research | Deep analysis | 10+ sections | Sonnet | $0.025 |
| breakfast_headlines | Headlines | Numbered list | Haiku | $0.002 |

### Output
Each email assigned to appropriate handler for Step 6.

### Design Notes
- Multiple tags can map to same handler (efficiency)
- Default handler for unrecognized tags
- Easy to add new handlers - just add to mapping

---

## Step 6: RUN Appropriate Enrichment Handler

### Purpose
Execute AI-powered enrichment using content-specific handler.

### File
`src/main/unified_adaptive_enrichment.py`

### Process

1. **Load Handler Modules**
   ```python
   from handlers.newsbrief_handler import enrich_newsbrief
   from handlers.gold_standard_enhanced_handler import enrich_gold_standard
   from handlers.itau_daily_handler import enrich_itau_daily
   # ... import all 21 handlers
   ```

2. **For Each Unenriched Email**
   ```python
   for email in unenriched_emails:
       tag = email['sender_tag']
       handler = TAG_TO_RULE[tag]
       
       # Extract clean content
       clean_content = extract_text_from_html(email['content_html'])
       
       # Route to appropriate handler
       if handler == 'newsbrief':
           result = enrich_newsbrief(
               title=email['title'],
               content=clean_content[:15000],
               content_html=email['content_html']
           )
       
       elif handler == 'gold_standard':
           result = enrich_gold_standard(
               title=email['title'],
               content=clean_content[:15000]
           )
       
       # ... etc for all handlers
   ```

3. **Handler Calls Claude AI**
   ```python
   # Inside newsbrief_handler.py
   def enrich_newsbrief(title, content, content_html):
       client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
       
       prompt = """
       Extract ALL the individual news stories from this briefing email.
       
       For each story:
       - Number it (1., 2., 3., etc.)
       - Extract the full headline
       - Add 2-4 bullet points with key details
       
       Format:
       <strong style="font-size:19px">1. [Full Headline]</strong>
       • Key point 1
       • Key point 2
       
       DO NOT include market snapshots or non-story content.
       """
       
       response = client.messages.create(
           model="claude-3-haiku-20240307",
           max_tokens=2048,
           messages=[{"role": "user", "content": prompt + content}]
       )
       
       enrichment = response.content[0].text
       
       return {
           'enriched_content': f"Rule: NewsBrief\n\n{enrichment}",
           'ai_score': 8.0
       }
   ```

4. **Return Enrichment**
   ```python
   # Result format
   {
       'enriched_content': 'Rule: NewsBreif\n\n1. Story...\n2. Story...',
       'ai_score': 8.5,
       'actors': '',  # Filled in Step 7
       'themes': ''   # Optional
   }
   ```

### Handler Examples

**NewsBreif Output:**
```
Rule: NewsBrief

<strong style="font-size:19px">1. Dollar Gains on Fed Comments</strong>
• Federal Reserve signals patient approach to rate cuts
• Dollar index up 0.5% to 104.2
• Market pricing in June cut probability drops to 40%

<strong style="font-size:19px">2. China Trade Data Disappoints</strong>
• Exports fell 2.3% year-over-year in October
• Imports declined 1.8%, below economist expectations
• Weak domestic demand concerns resurface among analysts
```

**Gold Standard Output:**
```
Rule: Gold Standard Enhanced

Today's Focus
Goldman Sachs revises Fed rate cut forecast following stronger employment data.

Main Analysis
• Fed Policy Shift: Goldman now expects first cut in September (vs June)
• Data Justification: 250k jobs added vs 180k expected, unemployment 3.7%
• Market Implications: 2-year yields up 15bp to 4.85%
• Historical Context: Similar 2019 revisions delayed cuts by 3 months
• Goldman's View: "Labor market gives Fed flexibility to stay restrictive"

Quick Hits
• S&P 500 down 1.2% on delayed cut expectations
• Dollar strengthens, EUR/USD at 1.08
```

### Output
Enriched content with "Rule: [Name]" label prepended.

### Technical Notes
- Each handler has specific Claude prompt
- Models vary: Sonnet (deep), Haiku (simple)
- Costs range from $0.002 to $0.025 per email
- Handlers can extract actors/themes or not
- All include rule label for transparency

---

## Step 7: EXTRACT Keywords (Option C Hybrid)

### Purpose
Extract 4-6 specific, meaningful keywords (no generic terms).

### File
`src/main/keyword_extractor.py`

### Process - 3-Step Hybrid Approach

**Step 7A: Regex Pre-Filter**
```python
import re

def regex_prefilter(text):
    """Remove generic patterns before AI"""
    patterns = [
        r'\b(breaking|latest|top)\s+(news|updates?|headlines?)\b',
        r'\bmarket\s+(updates?|news|highlights?|roundup)\b',
        r'\b(daily|weekly|monthly)\s+(brief|report|summary)\b',
    ]
    
    cleaned = text
    for pattern in patterns:
        cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
    
    return cleaned

# Example:
# Input:  "Breaking News: China's Latest Market Updates"
# Output: "China's Trade"
```

**Step 7B: AI Extraction**
```python
def extract_keywords_ai(title, content):
    client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
    
    # Detect language
    is_portuguese = any(word in content.lower() 
                       for word in ['notícias', 'hoje', 'brasil'])
    
    prompt = f"""
    Extract 4-6 SPECIFIC KEYWORDS from this financial story.
    
    ✅ GOOD KEYWORDS (concrete):
    - Companies: "Apple", "Tesla", "Petrobras"
    - Topics: "AI Chips", "Trade War", "Interest Rate Cut"
    - People: "Jerome Powell", "Elon Musk"
    - Places: "China", "Brazil", "Federal Reserve"
    
    ❌ BAD KEYWORDS (avoid):
    - "Breaking News", "Analysis", "Market Updates"
    - "Notícias", "Mercado", "Análise"
    
    Return ONLY keywords separated by " • "
    Maximum 6 keywords.
    
    {is_portuguese and 'This is Portuguese content. Extract in Portuguese.' or ''}
    
    Story:
    Title: {title}
    Content: {content[:2000]}
    
    Keywords:"""
    
    response = client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=150,
        messages=[{"role": "user", "content": prompt}]
    )
    
    return response.content[0].text.strip()
```

**Step 7C: Post-Processing Filter**
```python
def filter_exclusions(keywords_text):
    """Remove generic terms from AI output"""
    
    # Load exclusion list (89 terms)
    with open('config/keyword_exclusions.json', 'r') as f:
        exclusions = json.load(f)
    
    # Flatten all categories
    all_exclusions = []
    for category in exclusions.values():
        all_exclusions.extend(category)
    
    # Split keywords
    keyword_list = [k.strip() for k in keywords_text.split('•')]
    
    # Filter out exclusions (case-insensitive)
    filtered = []
    for keyword in keyword_list:
        is_excluded = any(
            excl.lower() == keyword.lower() 
            for excl in all_exclusions
        )
        
        if not is_excluded:
            filtered.append(keyword)
    
    return ' • '.join(filtered)

# Example:
# AI gave: "China • Trade War • Breaking News • Tariffs"
# After filter: "China • Trade War • Tariffs"
```

**Complete Function:**
```python
def extract_keywords(title, content, sender_tag=""):
    # Step 7A: Pre-filter
    cleaned_title = regex_prefilter(title)
    cleaned_content = regex_prefilter(content[:2000])
    
    # Step 7B: AI extraction
    keywords_raw = extract_keywords_ai(cleaned_title, cleaned_content)
    
    # Step 7C: Post-filter
    keywords_final = filter_exclusions(keywords_raw)
    
    return keywords_final if keywords_final else "Financial News"
```

### Exclusion List Structure
```json
{
  "meta_descriptions_en": [
    "Breaking News", "Market Updates", "Analysis", "Report"
  ],
  "meta_descriptions_pt": [
    "Notícias", "Análise", "Resumo", "Relatório"
  ],
  "generic_financial_en": [
    "Markets", "Trading", "Investors", "Stocks"
  ],
  "generic_financial_pt": [
    "Mercados", "Investidores", "Ações"
  ],
  "time_references_en": [
    "Today", "This Week", "Daily"
  ],
  "time_references_pt": [
    "Hoje", "Esta Semana", "Diário"
  ],
  "source_names": [
    "Bloomberg", "WSJ", "Reuters", "Barron's"
  ]
}
```

### Output
4-6 specific keywords (stored in `actors` database field).

### Examples

**English:**
- Input: "Breaking News: China Announces Tariffs on US Goods"
- Output: "China • Tariffs • Trade War • US Goods"

**Portuguese:**
- Input: "Análise: Petrobras anuncia dividendos extraordinários"
- Output: "Petrobras • Dividendos • Geração de Caixa • Acionistas"

### Technical Notes
- Model: Claude Haiku ($0.001 per extraction)
- Bilingual: Auto-detects Portuguese
- Cost-effective: Same as before, better quality
- Managed via Admin UI (8543) → Keyword Exclusions tab

---

## Step 8: SAVE Enriched Data to Database

### Purpose
Persist all enrichment results (from Steps 6-7) back to database.

### Process

1. **Collect Enrichment Data**
   ```python
   enrichment_data = {
       'enriched_content': result_from_step6,
       'actors': keywords_from_step7,
       'ai_score': score_from_step6,
       'themes': themes_from_step6  # Optional
   }
   ```

2. **Update Database Record**
   ```python
   # For regular emails (non-NewsBreif)
   db = lancedb.connect('s3://sage-unified-feed-lance/lancedb/')
   table = db.open_table('unified_feed')
   
   # Update by ID
   df = table.to_pandas()
   df.loc[df['id'] == email_id, 'enriched_content'] = enrichment_data['enriched_content']
   df.loc[df['id'] == email_id, 'actors'] = enrichment_data['actors']
   df.loc[df['id'] == email_id, 'ai_score'] = enrichment_data['ai_score']
   
   # Save back to LanceDB
   table.delete("id IS NOT NULL")  # Clear table
   table.add(df)  # Re-add with updates
   ```

3. **For NewsBreif: Create New Entries**
   ```python
   # NewsBreif creates SEPARATE entries for each story
   # (See NewsBreif Special Processing section below)
   
   for story in split_stories:
       new_entry = {
           'id': f"{original_email_id}_story_{i}",
           'sender_tag': f"{original_tag}- Newsbrief",
           'title': story['title'],
           'enriched_content': story['content'],
           'actors': story['keywords'],
           'link': story['link'],
           'content_html': original_email['content_html'],
           'created_at': original_email['created_at'],
           'ai_score': 8.0
       }
       
       table.add(pd.DataFrame([new_entry]))
   ```

### Final Database Record

**Regular Email:**
```python
{
    'id': 'hash-abc123',
    'source_type': 'email',
    'created_at': '2025-11-03T10:00:00Z',
    'sender_tag': 'goldman_sachs',
    'title': 'Q4 Economic Outlook',
    'content_html': '<html>...</html>',
    'content_text': 'Plain text...',
    'enriched_content': 'Rule: Gold Standard\n\nToday's Focus...',
    'actors': 'Fed • Jerome Powell • Interest Rates • Inflation',
    'ai_score': 8.5,
    'link': '',
    'custom_fields': '{}'
}
```

**NewsBreif Story:**
```python
{
    'id': 'hash-xyz_story_0',
    'source_type': 'email',
    'created_at': '2025-11-03T06:00:00Z',
    'sender_tag': 'bloomberg- Newsbrief',
    'title': '1. Dollar Gains on Fed Comments',
    'content_html': '<html>Original digest email...</html>',
    'enriched_content': '• Fed signals patient approach\n• Dollar up 0.5%',
    'actors': 'Fed • Jerome Powell • Dollar • Treasury Yields',
    'ai_score': 8.0,
    'link': 'https://bloomberg.com/news/dollar-gains',
    'custom_fields': '{}'
}
```

### Output
Fully enriched emails ready for display on port 8540.

### Technical Notes
- LanceDB on S3 creates new versions for updates
- No traditional transactions - use idempotent operations
- Log enrichment timestamps for debugging
- Handle partial failures gracefully

---

## NewsBreif Special Processing

### The Two-Component System

NewsBreif is unique - it's both a normal handler AND has post-processing.

### Component 1: NewsBreif Handler (Step 6)

**Execution:** Like any other handler  
**Input:** Full digest email (1 email with 6-12 stories)  
**Output:** Single enrichment with ALL stories formatted

```
Bloomberg Morning Briefing (1 email)
    ↓
NewsBreif Handler
    ↓
Claude AI extracts ALL stories
    ↓
Returns: 
"""
Rule: NewsBrief

1. Story headline
• Bullet 1
• Bullet 2

2. Another story
• Details...

...6 stories total
"""
```

**Cost:** $0.015 (one AI call for all stories)

### Component 2: NewsBreif Splitting (Between Steps 6-8)

**When:** After handler execution, before keyword extraction  
**Input:** The single enrichment with all stories  
**Output:** Multiple individual story objects

```python
def split_newsbrief_enrichment(enrichment_text, original_email):
    """
    Parse NewsBreif enrichment into individual stories
    """
    stories = []
    
    # Find all numbered stories
    story_pattern = r'<strong[^>]*>(\d+)\.\s+([^<]+)</strong>(.*?)(?=<strong|$)'
    matches = re.findall(story_pattern, enrichment_text, re.DOTALL)
    
    for number, title, content in matches:
        story = {
            'number': number,
            'title': f"{number}. {title.strip()}",
            'content': content.strip(),
            'original_email_html': original_email['content_html']
        }
        stories.append(story)
    
    return stories

# Example output:
# [
#   {number: '1', title: '1. Dollar Gains...', content: '• Fed signals...\n• Dollar up...'},
#   {number: '2', title: '2. China Trade...', content: '• Exports fell...\n• Imports down...'},
#   ...
# ]
```

### Integration in Step 6-8 Flow

```python
# Inside unified_adaptive_enrichment.py

for email in unenriched_emails:
    handler = get_handler(email['sender_tag'])
    
    # Step 6: Run handler
    enrichment = execute_handler(handler, email)
    
    # DECISION POINT: NewsBreif or regular?
    if handler in ['newsbrief', 'newsbrief_portuguese', 'newsbrief_portuguese_with_links']:
        
        # ═══════════════════════════════════
        # NEWSBRIEF PATH (Creates multiple entries)
        # ═══════════════════════════════════
        
        # Split into individual stories
        stories = split_newsbrief_enrichment(enrichment['enriched_content'], email)
        
        # For EACH story:
        for i, story in enumerate(stories):
            # Step 7: Extract keywords for THIS story
            keywords = extract_keywords(story['title'], story['content'])
            
            # Match article link for THIS story
            link = smart_match_link(story['title'], email['content_html'])
            
            # Step 8: CREATE new database entry
            new_entry = {
                'id': f"{email['id']}_story_{i}",
                'sender_tag': f"{email['sender_tag']}- Newsbrief",
                'title': story['title'],
                'enriched_content': story['content'],
                'actors': keywords,
                'link': link,
                'content_html': email['content_html'],
                'created_at': email['created_at'],
                'ai_score': 8.0
            }
            
            save_to_database(new_entry)
        
        # Mark original email as "split"
        mark_as_processed(email['id'])
    
    else:
        
        # ═══════════════════════════════════
        # REGULAR PATH (Updates existing entry)
        # ═══════════════════════════════════
        
        # Step 7: Extract keywords for whole email
        keywords = extract_keywords(email['title'], enrichment['enriched_content'])
        
        # Step 8: UPDATE existing database entry
        update_database(email['id'], {
            'enriched_content': enrichment['enriched_content'],
            'actors': keywords,
            'ai_score': enrichment.get('ai_score', 0.0)
        })
```

### Why This Architecture?

**Efficient:**
- ONE AI call extracts all stories ($0.015)
- Splitting is text parsing (free)
- Keyword extraction per story ($0.001 × 6 = $0.006)
- **Total: $0.021 per digest**

vs.

**Alternative (Split First, Then Enrich Each):**
- Split into 6 stories first
- Enrich each story separately ($0.015 × 6 = $0.09)
- **Total: $0.09 per digest (4x more expensive!)**

### Result
- 1 digest email → 6 individual story cards
- Each with own title, keywords, link
- Better UX, same cost

---

## Complete Flow Summary

### For Regular Emails (Goldman Sachs, Itau, etc.)
```
1 Email
    ↓
Steps 1-4: Fetch, Filter, Tag, Store
    ↓
1 Database Entry (raw)
    ↓
Steps 5-6: Map, Enrich
    ↓
1 Enrichment
    ↓
Step 7: Keywords
    ↓
1 Set of Keywords
    ↓
Step 8: Update Entry
    ↓
1 Database Entry (enriched)
    ↓
1 Card on Display
```

### For NewsBreif Digests (Bloomberg, WSJ, Reuters, Barron's)
```
1 Digest Email (6 stories inside)
    ↓
Steps 1-4: Fetch, Filter, Tag, Store
    ↓
1 Database Entry (raw digest)
    ↓
Steps 5-6: Map, Enrich
    ↓
1 Enrichment (all 6 stories formatted)
    ↓
NewsBreif Split
    ↓
6 Individual Stories
    ↓
For EACH story:
    Step 7: Keywords
    Step 8: Create Entry
    ↓
6 Database Entries (enriched stories)
    ↓
6 Cards on Display
```

---

## Data Transformation Example

**Starting Email (Bloomberg):**
```
From: bloomberg@bloomberg.com
Subject: Morning Briefing
Body: <html>
  Story 1: Dollar gains...
  Story 2: China trade...
  Story 3: Tech rally...
  ...6 stories total
</html>
```

**After Step 4 (Store):**
```python
{
  'id': 'hash-abc',
  'sender_tag': 'bloomberg',
  'title': 'Morning Briefing',
  'content_html': '<html>...</html>',
  'enriched_content': '',  # Empty
  'actors': '',  # Empty
}
```

**After Step 6 (Enrich):**
```python
{
  'enriched_content': '''
    Rule: NewsBrief
    
    1. Dollar Gains...
    • Fed signals...
    
    2. China Trade...
    • Exports fell...
    
    ...6 stories
  '''
}
```

**After NewsBreif Split + Steps 7-8:**
```python
# 6 separate database entries created:

Entry 1:
{
  'id': 'hash-abc_story_0',
  'sender_tag': 'bloomberg- Newsbrief',
  'title': '1. Dollar Gains...',
  'enriched_content': '• Fed signals...\n• Dollar up...',
  'actors': 'Fed • Jerome Powell • Dollar',
  'link': 'https://bloomberg.com/news/dollar-gains'
}

Entry 2:
{
  'id': 'hash-abc_story_1',
  'sender_tag': 'bloomberg- Newsbrief',
  'title': '2. China Trade...',
  'enriched_content': '• Exports fell...\n• Imports down...',
  'actors': 'China • Trade War • Exports',
  'link': 'https://bloomberg.com/news/china-trade'
}

... 4 more entries
```

**On Display (8540):**
- User sees 6 individual cards
- Each clickable, with own keywords
- Each with specific article link (or HTML popup)

---

## File Flow Reference

| Step | File(s) | Input | Output |
|------|---------|-------|--------|
| 1 | sage4_gmail_robust.py | Gmail IMAP | Raw emails |
| 2 | allowed_senders.json | Raw emails | Filtered emails |
| 3 | tag_detection_rules.json | Filtered emails | Tagged emails |
| 4 | LanceDB write | Tagged emails | Stored emails |
| 5 | tag_to_rule_mapping.py | sender_tag | handler name |
| 6 | unified_adaptive_enrichment.py + handlers/* | Stored email | Enrichment |
| 7 | keyword_extractor.py + keyword_exclusions.json | Title + content | Keywords |
| 8 | LanceDB update | Enrichment + keywords | Final entry |

---

## Next Steps

1. **Understand the Flow:** Read this document completely
2. **See NewsBreif Details:** Read [docs/03-NEWSBRIEF-ARCHITECTURE.md](03-NEWSBRIEF-ARCHITECTURE.md)
3. **Plan Automation:** Read [docs/07-CRON-DESIGN.md](07-CRON-DESIGN.md)
4. **Customize:** Use Admin Interface (docs/06-ADMIN-INTERFACE.md)

---

**This is your complete blueprint for understanding and recreating the SAGE processing pipeline.**
