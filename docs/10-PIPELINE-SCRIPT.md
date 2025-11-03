# Unified Pipeline Script

**One script to run the complete 8-step process with multiple modes**

---

## Overview

`run_pipeline.py` is the unified entry point for all SAGE processing operations. It handles the complete 8-step pipeline with different execution modes for various use cases.

---

## Installation

The script is located at: `src/main/run_pipeline.py`

**Setup:**
```bash
cd /home/ubuntu/newspaper_project
export ANTHROPIC_API_KEY="your-api-key"
export GMAIL_USER="your_email@gmail.com"  
export GMAIL_APP_PASSWORD="your-app-password"
```

---

## Usage Modes

### Mode 1: Fetch New Emails
```bash
python3 run_pipeline.py --fetch-new
```

**What it does:**
- Complete 8-step pipeline (Steps 1-8)
- Fetches from Gmail (last 24 hours)
- Filters allowed senders
- Detects tags
- Stores to database
- Enriches with handlers
- Handles NewsBreif splitting automatically
- Extracts keywords
- Saves enrichment

**Use cases:**
- Manual email processing
- Testing new handlers
- Recovering from errors

---

### Mode 2: Re-Enrich Latest N
```bash
python3 run_pipeline.py --reenrich --last 10
```

**What it does:**
- Steps 5-8 only (no Gmail fetch)
- Gets latest 10 emails from database
- For NewsBreif: Deletes old stories, creates new ones
- Re-runs enrichment with current handlers
- Re-extracts keywords with Option C
- Updates database

**Use cases:**
- Testing new keyword extraction (Option C)
- Updating after handler improvements
- Fixing poorly enriched emails
- Testing new NewsBreif splitting logic

**Example:**
```bash
# After improving keyword extraction, refresh latest emails
python3 run_pipeline.py --reenrich --last 10

# Result: Latest 10 emails now have better keywords
```

---

### Mode 3: Enrich Unenriched (For Cron)
```bash
python3 run_pipeline.py --enrich-unenriched
```

**What it does:**
- Steps 5-8 only
- Finds ALL unenriched emails in database
- Enriches each one
- Handles NewsBreif splitting
- Extracts keywords
- Saves enrichment

**Use cases:**
- Cron Job Stage 2 (primary use)
- Catching up on backlog
- After manual Gmail import

**Cron integration:**
```bash
# In crontab:
*/15 * * * * cd /home/ubuntu/newspaper_project && python3 run_pipeline.py --enrich-unenriched
```

---

### Mode 4: Recreate Database
```bash
python3 run_pipeline.py --recreate-db
```

**What it does:**
- Drops existing database table
- Fetches 10-15 recent emails from Gmail
- Filters and tags them
- Creates fresh database table
- Enriches all emails
- Handles NewsBreif splitting

**Use cases:**
- Starting fresh
- Testing complete flow
- Database corruption recovery
- Demo/presentation setup

**Warning:** Destroys existing data!

---

### Mode 5: Re-Enrich Specific Email
```bash
python3 run_pipeline.py --enrich-id abc123
```

**What it does:**
- Steps 5-8 on one specific email
- Finds email by ID
- Re-enriches with current handler
- Updates keywords
- Saves

**Use cases:**
- Fixing one problem email
- Testing handler on specific email
- Manual corrections

---

## NewsBreif Handling

### Automatic Detection

The script automatically detects NewsBreif emails and handles splitting:

```python
if handler in ['newsbrief', 'newsbrief_portuguese', 'newsbrief_portuguese_with_links']:
    # Split into individual stories
    # Extract keywords per story
    # Create multiple database entries
```

**No special flags needed - it just works!**

### Example

```bash
python3 run_pipeline.py --fetch-new
```

**If Bloomberg digest found:**
```
📧 Email: Morning Briefing: Markets Digest Fed Comments...
   Tag: bloomberg → Handler: newsbrief
   🤖 Running newsbrief handler...
   ✅ Enrichment: 3200 chars
   📰 NewsBreif detected - splitting stories...
   Found 6 stories
   🔑 Story 1: Extracting keywords...
   ✅ Saved story 1: Fed • Jerome Powell • Dollar
   🔑 Story 2: Extracting keywords...
   ✅ Saved story 2: China • Trade War • Exports
   ...
   ✅ Saved story 6: Corporate Earnings • Q4
```

**Result:** 6 individual cards on port 8540!

---

## Error Handling

### Graceful Failures
```python
# If one email fails, others still process
try:
    enrichment = execute_handler(handler, email)
except Exception as e:
    print(f"❌ Error: {e}")
    continue  # Skip this email, process next
```

### Duplicate Detection
```python
# Automatically skips duplicate emails
existing = table.search().where(f"id = '{email_id}'")
if not existing.empty:
    continue  # Skip
```

---

## Logging

### Console Output
Detailed progress for each step:
```
================================================================================
MODE: FETCH NEW EMAILS (Complete Pipeline)
================================================================================

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 1: FETCH from Gmail
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📥 Connecting to Gmail IMAP...
   Found 5 emails from last 24 hours
✅ Fetched 5 emails successfully

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 2: FILTER by allowed senders
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

...etc
```

### Log to File
```bash
# Redirect output to log file
python3 run_pipeline.py --fetch-new >> /home/ubuntu/logs/pipeline.log 2>&1
```

---

## Integration with Cron

### Recommended Cron Setup

**Cron 1: Fetch New (Every 30 min)**
```bash
0,30 * * * * cd /home/ubuntu/newspaper_project && python3 run_pipeline.py --fetch-new >> /home/ubuntu/logs/fetch.log 2>&1
```

**Cron 2: Enrich Backlog (Every 15 min)**
```bash
*/15 * * * * cd /home/ubuntu/newspaper_project && python3 run_pipeline.py --enrich-unenriched >> /home/ubuntu/logs/enrich.log 2>&1
```

**Benefits:**
- Same script for manual and automated use
- Consistent behavior
- Easy to test (run manually first)
- One script to maintain

---

## Examples

### Example 1: Fresh Start
```bash
# Create fresh database with 10-15 recent emails
python3 run_pipeline.py --recreate-db

# Output:
# - Drops old database
# - Fetches 10-15 emails
# - Enriches all
# - NewsBreif emails split into stories
# - Ready to view on port 8540
```

### Example 2: Test New Keywords
```bash
# After modifying keyword_exclusions.json
python3 run_pipeline.py --reenrich --last 10

# Output:
# - Re-enriches latest 10 emails
# - Uses new Option C extraction
# - New keywords applied
# - NewsBreif stories recreated if applicable
```

### Example 3: Daily Automation
```bash
# Set in crontab
0,30 * * * * python3 run_pipeline.py --fetch-new
*/15 * * * * python3 run_pipeline.py --enrich-unenriched

# Result:
# - New emails fetched every 30 min
# - Enrichment runs every 15 min
# - NewsBreif splitting automatic
# - Fully automated system
```

---

## Comparison to Old Scripts

### Before (Multiple Scripts)
```bash
./recreate_database.sh          # Database recreation
./fetch_and_split.py            # Fetch and split
python3 unified_adaptive_enrichment.py --last 10  # Re-enrich
```

### After (One Script)
```bash
python3 run_pipeline.py --recreate-db    # Same as recreate_database.sh
python3 run_pipeline.py --fetch-new      # Same as fetch_and_split.py
python3 run_pipeline.py --reenrich --last 10  # Same as enrichment
```

**Benefits:**
- ✅ One script instead of three
- ✅ Consistent interface
- ✅ NewsBreif handling built-in
- ✅ Option C keywords automatic
- ✅ Easier to understand and maintain

---

## Technical Notes

### NewsBreif Detection
Automatic based on handler name:
```python
NEWSBRIEF_HANDLERS = [
    'newsbrief',
    'newsbrief_portuguese',
    'newsbrief_portuguese_with_links'
]
```

### Database Operations
- Reads from: `s3://sage-unified-feed-lance/lancedb/unified_feed`
- Updates in place for regular emails
- Creates new entries for NewsBreif stories
- Handles S3 sync automatically

### Dependencies
All standard SAGE dependencies:
- lancedb
- pandas
- anthropic
- beautifulsoup4

---

## Next Steps

1. **Test the script:**
   ```bash
   python3 run_pipeline.py --reenrich --last 5
   ```

2. **Verify NewsBreif splitting:**
   - Check if Bloomberg digest splits into stories
   - Verify each story has own keywords
   - Check links match correctly

3. **Set up cron:**
   - Use `--fetch-new` for Stage 1
   - Use `--enrich-unenriched` for Stage 2

---

**This unified script replaces multiple scattered scripts with one clean interface!**
