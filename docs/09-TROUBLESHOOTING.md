# Troubleshooting Guide

## Common Issues

### Admin Interface

**Problem:** Edit buttons show "coming soon"
**Cause:** Browser caching
**Solution:** Use Incognito mode (Ctrl+Shift+N)

**Problem:** Keyword Exclusions tab empty
**Cause:** Browser cache or API issue
**Solution:** Hard refresh (Ctrl+Shift+R), check console (F12)

---

### Main Interface

**Problem:** No emails showing
**Cause:** Database empty or API error
**Solution:** Run `./recreate_database.sh`

**Problem:** "No summary available"
**Cause:** Emails not enriched
**Solution:** Run `python3 unified_adaptive_enrichment.py --last 100`

**Problem:** Keywords showing "Breaking News"
**Cause:** Old keyword extraction
**Solution:** Re-enrich with new extractor

---

### Keyword Extraction

**Problem:** Generic keywords still appearing
**Cause:** Not using Option C or exclusion list incomplete
**Solution:** Add terms to keyword_exclusions.json via Admin (8543)

**Problem:** Portuguese keywords in English
**Cause:** Language detection failed
**Solution:** Check content has Portuguese words

---

### NewsBreif

**Problem:** Digest showing as one card
**Cause:** Splitting not running
**Solution:** Check handler is 'newsbrief' in tag_to_rule_mapping

**Problem:** Links not working
**Cause:** Link matching confidence too low
**Solution:** Use HTML popup fallback

---

### Database

**Problem:** ArrowTypeError on save
**Cause:** Data type mismatch
**Solution:** Ensure created_at is ISO string, scores are floats

**Problem:** Table not found
**Cause:** Database path incorrect
**Solution:** Check s3://sage-unified-feed-lance/lancedb/

---

## Logs

### Check Logs
```bash
tail -f /home/ubuntu/logs/fetch.log
tail -f /home/ubuntu/logs/enrich.log
tail -f /home/ubuntu/newspaper_project/sage.log
```

### Enable Debug Logging
```bash
export LOG_LEVEL=DEBUG
python3 sage4_interface_fixed.py
```
