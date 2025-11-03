# NewsBreif Architecture - Deep Dive

**How digest emails are transformed into individual story cards**

---

## The Challenge

Bloomberg, WSJ, Reuters, Barron's, and FT all send "briefing" or "digest" emails:
- **One email** contains 6-12 separate news stories
- Each story is distinct (different topic, different article)
- Displaying as one card creates a massive wall of text

---

## The Solution: Two-Component Architecture

NewsBreif uses a **hybrid approach**:
1. **Component 1:** Normal handler (extracts ALL stories in one AI call)
2. **Component 2:** Post-processing splitter (creates individual entries)

---

## Component 1: NewsBreif Handler

### Execution
Runs during **Step 6 (ENRICH)** like any other handler.

### Input
One digest email with 6-12 stories embedded in HTML.

### Process
```python
# handlers/newsbrief_handler.py

def enrich_newsbrief(title, content, content_html):
    client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
    
    prompt = """
    Extract ALL the individual news stories from this briefing email.
    
    For each story:
    - Number it (1., 2., 3., etc.)
    - Extract the FULL story headline
    - Add 2-4 bullet points with key details
    
    Format each story:
    <strong style="font-size:19px; display:block; margin-top:15px;">1. [Full Headline]</strong>
    • Key point with specific data
    • Another key point with names/numbers
    • Supporting detail
    
    DO NOT include:
    - Market snapshots (S&P 500, DJIA, etc.)
    - Non-story content
    - Table of contents
    
    Extract ONLY the actual news stories.
    
    Email content:
    {content}
    """
    
    response = client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}]
    )
    
    enrichment = response.content[0].text
    
    return {
        'enriched_content': f"Rule: NewsBrief\n\n{enrichment}",
        'ai_score': 8.0
    }
```

### Output
**Single enrichment** containing ALL formatted stories:

```
Rule: NewsBrief

<strong style="font-size:19px">1. Dollar Gains on Fed Comments</strong>
• Federal Reserve signals patient approach to rate cuts
• Dollar index up 0.5% to 104.2, strongest since March
• Market pricing in June cut probability drops to 40%

<strong style="font-size:19px">2. China Trade Data Disappoints</strong>
• Exports fell 2.3% year-over-year in October  
• Imports declined 1.8%, below 1.2% economist forecast
• Weak domestic demand concerns resurface among analysts

<strong style="font-size:19px">3. Tech Stocks Rally on AI Optimism</strong>
• Nasdaq up 1.5% led by semiconductor sector
• Nvidia gains 3.2% on strong data center demand
• AI infrastructure spending estimates revised higher

...6 stories total in ONE enrichment
```

### Cost
**$0.015 per digest** (one AI call, regardless of story count)

### Key Point
**At this point, NewsBreif works exactly like Gold Standard or Itau Daily:**
- One email in → One enrichment out
- Stored as `enriched_content` in database
- No splitting yet

---

## Component 2: NewsBreif Splitting

### Execution
Runs **between Steps 6-8** (after enrichment, before keywords/save).

### Trigger
Detected automatically:
```python
if handler in ['newsbrief', 'newsbrief_portuguese', 'newsbrief_portuguese_with_links']:
    # Activate splitting logic
```

### Process

**Step 1: Parse Enrichment**
```python
def split_newsbrief_enrichment(enrichment_text, original_email):
    """
    Parse the single enrichment into individual story objects
    """
    stories = []
    
    # Regex pattern to find numbered stories
    # Looks for: <strong...>1. Title</strong>Content...
    pattern = r'<strong[^>]*>(\d+)\.\s+([^<]+)</strong>(.*?)(?=<strong|$)'
    
    matches = re.findall(pattern, enrichment_text, re.DOTALL)
    
    for number, title, content in matches:
        story = {
            'number': number,
            'title': f"{number}. {title.strip()}",
            'content': content.strip(),
            'original_email_html': original_email['content_html'],
            'original_email_id': original_email['id'],
            'created_at': original_email['created_at']
        }
        stories.append(story)
    
    return stories

# Example output:
# [
#   {number: '1', title: '1. Dollar Gains on Fed Comments', content: '• Fed signals...\n• Dollar up...'},
#   {number: '2', title: '2. China Trade Data Disappoints', content: '• Exports fell...'},
#   ...6 stories
# ]
```

**Step 2: Extract Keywords Per Story**
```python
for story in stories:
    # Step 7: Keywords for THIS specific story
    keywords = extract_keywords(story['title'], story['content'])
    
    story['keywords'] = keywords
```

**Step 3: Match Links Per Story**
```python
from smart_link_matcher import match_story_to_link

for story in stories:
    # Smart title-to-URL matching
    link = match_story_to_link(
        story_title=story['title'],
        email_html=original_email['content_html']
    )
    
    story['link'] = link or ''  # Empty if no match (will use HTML popup)
```

**Step 4: Create Database Entries**
```python
for i, story in enumerate(stories):
    # Step 8: CREATE new database entry for each story
    new_entry = {
        'id': f"{original_email['id']}_story_{i}",
        'source_type': 'email',
        'created_at': original_email['created_at'],
        'sender_tag': f"{original_email['sender_tag']}- Newsbrief",
        'title': story['title'],
        'content_html': original_email['content_html'],  # Keep original
        'content_text': story['content'],
        'enriched_content': story['content'],
        'actors': story['keywords'],
        'themes': '',
        'ai_score': 8.0,
        'link': story['link'],
        'custom_fields': '{}'
    }
    
    # Add to database
    table.add(pd.DataFrame([new_entry]))
```

**Step 5: Mark Original**
```python
# Update original email to show it was split
df.loc[df['id'] == original_email['id'], 'enriched_content'] = 'SPLIT_INTO_STORIES'
df.loc[df['id'] == original_email['id'], 'actors'] = f'Split into {len(stories)} stories'
```

### Output
**6 individual database entries** instead of 1.

---

## Integration with 8-Step Process

### Before NewsBreif (Regular Email Flow)
```
Steps 1-4: Fetch → Filter → Tag → Store
    ↓
1 email in database
    ↓
Steps 5-6: Map → Enrich
    ↓
1 enrichment
    ↓
Step 7: Keywords
    ↓
1 set of keywords
    ↓
Step 8: Save
    ↓
1 enriched entry
    ↓
1 card on display
```

### With NewsBreif (Special Flow)
```
Steps 1-4: Fetch → Filter → Tag → Store
    ↓
1 digest email in database
    ↓
Steps 5-6: Map → Enrich
    ↓
1 enrichment (with 6 stories inside)
    ↓
NEWSBRIEF SPLIT ← Special processing here
    ↓
6 story objects
    ↓
For EACH story:
    Step 7: Keywords
    Step 8: Create Entry
    ↓
6 enriched entries
    ↓
6 cards on display
```

### Where It Happens

**In unified_adaptive_enrichment.py (or enrich_complete.py for cron):**

```python
# After Step 6, before Steps 7-8

if handler == 'newsbrief':
    # Import splitting logic
    from utils.newsbrief_splitter import split_newsbrief_enrichment
    
    # Split the enrichment
    stories = split_newsbrief_enrichment(enrichment_text, original_email)
    
    # Process each story (Steps 7-8)
    for story in stories:
        keywords = extract_keywords(story)    # Step 7
        save_story_entry(story, keywords)     # Step 8
else:
    # Regular flow (Steps 7-8)
    keywords = extract_keywords(email, enrichment)  # Step 7
    update_email_entry(email, enrichment, keywords)  # Step 8
```

---

## Cost Analysis

### Efficiency Comparison

**Option A: Split First, Then Enrich (NOT USED)**
```
1 digest with 6 stories
    ↓
Split first (free)
    ↓
6 individual stories
    ↓
Enrich each separately
- Story 1: Claude API call ($0.015)
- Story 2: Claude API call ($0.015)
- Story 3: Claude API call ($0.015)
- Story 4: Claude API call ($0.015)
- Story 5: Claude API call ($0.015)
- Story 6: Claude API call ($0.015)
    ↓
Total: $0.09 per digest ❌ EXPENSIVE
```

**Option B: Enrich First, Then Split (USED)**
```
1 digest with 6 stories
    ↓
Enrich once (extract all 6 stories)
- Claude API call: $0.015
    ↓
Split enrichment (text parsing)
- Free (regex parsing)
    ↓
6 individual stories
    ↓
Keywords per story
- 6 × $0.001 = $0.006
    ↓
Total: $0.021 per digest ✅ EFFICIENT
```

**Savings: 77% cheaper! ($0.09 vs $0.021)**

### Cost Breakdown

| Operation | Cost | Count | Total |
|-----------|------|-------|-------|
| NewsBreif Handler | $0.015 | 1 | $0.015 |
| Splitting | $0.000 | 1 | $0.000 |
| Keyword Extraction | $0.001 | 6 | $0.006 |
| **Per Digest** | | | **$0.021** |
| **Per Story** | | | **$0.0035** |

**For 10 digests/day:**
- Daily: $0.21
- Monthly: $6.30
- Yearly: $76.65

**Extremely cost-effective for the value provided!**

---

## Link Matching Strategy

### Challenge
Each story needs its own article URL, but email HTML has all links mixed together.

### Solution: Smart Matching

```python
def match_story_to_link(story_title, email_html):
    """
    Match story title to article link using fuzzy matching
    """
    from difflib import SequenceMatcher
    
    # Extract all links from HTML
    links = extract_all_links(email_html)
    
    # Clean story title for comparison
    clean_title = story_title.lower()
    clean_title = re.sub(r'^\d+\.\s+', '', clean_title)  # Remove "1. "
    
    best_match = None
    best_score = 0
    
    for link in links:
        # Get link text/title
        link_text = link['text'].lower()
        
        # Calculate similarity
        similarity = SequenceMatcher(None, clean_title, link_text).ratio()
        
        # Calculate word overlap
        title_words = set(clean_title.split())
        link_words = set(link_text.split())
        overlap = len(title_words & link_words) / max(len(title_words), 1)
        
        # Combined score
        score = (0.6 * similarity) + (0.4 * overlap)
        
        if score > best_score and score > 0.4:  # Minimum 40% confidence
            best_score = score
            best_match = link['url']
    
    return best_match
```

### Accuracy by Source

| Source | Accuracy | Method |
|--------|----------|--------|
| Bloomberg | 100% | Smart matching |
| Barron's | 100% | Smart matching |
| WSJ Weekend | 100% | Positional matching |
| Folha | 100% | Smart matching |
| Reuters | 33% | Smart matching |
| Business Insider | 33% | Smart matching |
| **Overall** | **49%** | **Hybrid** |

### Fallback: HTML Popup

For stories without matched link (51%):
```python
if not story['link']:
    # Store original email HTML
    story['content_html'] = original_email['content_html']
    
    # Frontend will show "📧 View original email" button
    # Clicking opens beautiful HTML popup with full email
```

**Better than:** Google News search (often incorrect)  
**Provides:** Complete original email context

---

## Portuguese Support

### NewsBreif Portuguese Handler

Same architecture, Portuguese prompts:

```python
# handlers/newsbrief_portuguese_handler.py

prompt = """
Extraia TODAS as notícias individuais deste email de briefing.

Para cada notícia:
- Numere (1., 2., 3., etc.)
- Extraia o título completo
- Adicione 2-4 pontos-chave com detalhes

Formato:
<strong style="font-size:19px">1. [Título Completo]</strong>
• Ponto-chave 1
• Ponto-chave 2

NÃO inclua panoramas de mercado ou conteúdo não-notícia.
"""
```

### Sources
- **Estadão:** Brazilian newspaper (estadao.com.br)
- **Folha:** Brazilian newspaper (folha.com.br)

### Link Extraction
Works identically, detects Portuguese tracking URLs:
- `click.jornal.estadao.com.br`
- `click.folhadespaulo.com.br`

---

## Display on Interface

### Single Digest (Without Splitting)
```
┌──────────────────────────────────────────┐
│ @Bloomberg · Nov 3, 6:00 AM              │
│ Morning Briefing: Markets Digest...     │
│                                          │
│ Rule: NewsBrief                          │
│                                          │
│ 1. Dollar Gains...                       │
│ • Fed signals...                         │
│ • Dollar up...                           │
│                                          │
│ 2. China Trade...                        │
│ • Exports fell...                        │
│                                          │
│ ...4 more stories...                     │
│                                          │
│ ▼ MASSIVE CARD (hard to scan)            │
└──────────────────────────────────────────┘
```

### With Splitting (Current System)
```
┌──────────────────────────────────────────┐
│ @Bloomberg- Newsbrief · Nov 3, 6:00 AM   │
│ 1. Dollar Gains on Fed Comments          │
│ 🔑 Fed • Jerome Powell • Dollar          │
│ [Show More ▼]                            │
└──────────────────────────────────────────┘

┌──────────────────────────────────────────┐
│ @Bloomberg- Newsbrief · Nov 3, 6:00 AM   │
│ 2. China Trade Data Disappoints          │
│ 🔑 China • Trade War • Exports           │
│ [Show More ▼]                            │
└──────────────────────────────────────────┘

┌──────────────────────────────────────────┐
│ @Bloomberg- Newsbrief · Nov 3, 6:00 AM   │
│ 3. Tech Stocks Rally on AI Optimism      │
│ 🔑 Nasdaq • AI • Nvidia • Tech Stocks    │
│ [Show More ▼]                            │
└──────────────────────────────────────────┘

... 3 more story cards

✅ EASY TO SCAN
✅ Each clickable
✅ Individual keywords
✅ Individual links
```

---

## Integration in Cron

### Where Splitting Happens

**Inside Cron Stage 2 (enrich_complete.py):**

```python
for email in unenriched_emails:
    handler = get_handler(email['sender_tag'])
    
    # Step 6: Run handler (same for ALL emails)
    enrichment = execute_handler(handler, email)
    
    # DECISION POINT
    if handler in NEWSBRIEF_HANDLERS:
        
        # ═══════════════════════════════════════
        # NEWSBRIEF PATH
        # ═══════════════════════════════════════
        
        split_and_save_stories(email, enrichment)
        # └→ Internally: Parse → Extract keywords → Match links → Save entries
        
    else:
        
        # ═══════════════════════════════════════
        # REGULAR PATH
        # ═══════════════════════════════════════
        
        save_regular_enrichment(email, enrichment)
        # └→ Internally: Extract keywords → Update entry
```

### Why in Stage 2?

**✅ Advantages:**
- Happens after enrichment (has formatted stories to split)
- Happens before keywords (can extract per story)
- Natural place in flow
- No separate cron needed
- Automatic detection

**❌ Alternative (Separate Cron 3):**
- More complex architecture
- Coordination issues
- Another failure point
- No real benefit

### Timeline Example

```
10:00 AM → Stage 1 (Cron 1)
           └→ Fetches Bloomberg digest → Stores as 1 raw entry

10:15 AM → Stage 2 (Cron 2)
           ├→ Finds 1 unenriched email
           ├→ bloomberg tag → newsbrief handler
           ├→ Enrichment: Returns formatted 6 stories (1 AI call)
           ├→ SPLIT: Parse into 6 story objects
           ├→ For story 1: Keywords + Link + Save
           ├→ For story 2: Keywords + Link + Save
           ├→ For story 3: Keywords + Link + Save
           ├→ For story 4: Keywords + Link + Save
           ├→ For story 5: Keywords + Link + Save
           ├→ For story 6: Keywords + Link + Save
           └→ Result: 6 entries in database

10:16 AM → User refreshes port 8540
           └→ Sees 6 new individual story cards ✅
```

---

## Benefits of This Architecture

### User Experience
- ✅ Easy to scan (6 cards vs 1 massive card)
- ✅ Individual story links (49% real, 51% HTML popup)
- ✅ Keywords per story (more specific)
- ✅ Can mark individual stories as read/favorite

### Cost Efficiency
- ✅ One AI call extracts all stories ($0.015)
- ✅ Splitting is text parsing (free)
- ✅ 77% cheaper than separate enrichment

### Technical
- ✅ Scales to any number of stories
- ✅ Works for English and Portuguese
- ✅ Integrates cleanly into existing flow
- ✅ No architectural complexity

---

## Comparison: NewsBreif vs Regular Handler

### Regular Handler (Gold Standard)
```
Goldman Sachs email
    ↓
gold_standard handler
    ↓
1 enrichment
    ↓
1 keyword extraction
    ↓
1 database entry
    ↓
1 card

Cost: $0.025
Latency: ~15 seconds
```

### NewsBreif Handler
```
Bloomberg digest (6 stories)
    ↓
newsbrief handler
    ↓
1 enrichment (6 stories formatted)
    ↓
SPLIT
    ↓
6 stories
    ↓
6 keyword extractions
    ↓
6 link matchings
    ↓
6 database entries
    ↓
6 cards

Cost: $0.021 total ($0.0035 per story)
Latency: ~40 seconds total (~7 sec per story)
```

**NewsBreif is MORE efficient per story despite splitting!**

---

## Implementation Checklist

When implementing cron automation:

- [ ] Create `fetch_and_store.py` (Steps 1-4)
- [ ] Create `enrich_complete.py` (Steps 5-8)
- [ ] Include NewsBreif splitting logic in `enrich_complete.py`
- [ ] Test NewsBreif splitting with real Bloomberg email
- [ ] Verify 6 entries created from 1 digest
- [ ] Check keywords are story-specific
- [ ] Verify links match correctly
- [ ] Test HTML popup for unmatched links
- [ ] Install cron jobs
- [ ] Monitor logs for errors

---

## Future Enhancements

### Potential Improvements
1. **Parallel Processing** - Enrich multiple emails simultaneously
2. **Smart Scheduling** - Adjust frequency based on email volume
3. **Link Cache** - Remember matched links for similar titles
4. **Story Deduplication** - Detect same story from different sources

### Not Recommended
- Separate cron for splitting (unnecessary complexity)
- Split before enrichment (4x more expensive)
- Real-time processing (overkill for briefings)

---

**This architecture provides the optimal balance of UX, cost, and maintainability.**

For implementation details, see:
- [8-Step Process](02-8STEP-PROCESS.md) - Complete processing flow
- [Handlers Guide](05-HANDLERS-GUIDE.md) - NewsBreif handler details
- Code: `src/handlers/newsbrief_handler.py`
