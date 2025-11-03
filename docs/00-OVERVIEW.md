# SAGE System Overview

## What is SAGE?

**SAGE (Structured Aggregation & Generated Enrichment)** is a premium financial intelligence system that:
1. Fetches emails from curated sources (Goldman Sachs, Bloomberg, WSJ, etc.)
2. Filters to only allowed senders (22 premium sources)
3. Routes to specialized AI handlers (21 different enrichment rules)
4. Extracts specific keywords (no generic terms)
5. Displays in beautiful white Twitter-style interface

---

## Key Features

### ✅ Intelligent Email Processing
- **8-step pipeline** from Gmail to enriched display
- **21 specialized handlers** for different email types
- **Automatic routing** based on sender and content

### ✅ NewsBreif Story Splitting
- Digest emails → Individual story cards
- 1 Bloomberg briefing → 6 separate cards
- Better UX, individual links, per-story keywords

### ✅ Option C Keyword Extraction
- 3-step hybrid filtering
- 89 exclusion terms (generic words removed)
- Bilingual support (English + Portuguese)
- Focus on companies, topics, people, places

### ✅ Visual Admin Interface
- Manage 22 allowed senders
- Configure 16 tagging rules
- View 41 tag→handler mappings
- Edit 89 keyword exclusions

### ✅ Beautiful Interface
- White Twitter-style cards
- Show More/Less collapsible design
- HTML email popup for full content
- Load More pagination

---

## Use Cases

### Financial Professionals
- Track market-moving news from premium sources
- Get AI-enriched summaries (save time reading)
- Individual story cards (easy to scan)
- Specific keywords (find what matters)

### Researchers
- Organize financial intelligence
- Search by keywords
- Reference original emails (HTML popup)
- Export for analysis

### Traders
- Quick market updates
- Breaking news alerts
- Economic data releases
- Central bank communications

---

## System Stats

- **Sources:** 22 premium financial sources
- **Handlers:** 21 specialized AI enrichment rules
- **Keywords:** 4-6 specific terms per email
- **Exclusions:** 89 generic terms filtered
- **Languages:** English + Portuguese
- **Cost:** ~$7/month for 10 digests/day

---

## Quick Links

- [Architecture](01-ARCHITECTURE.md)
- [8-Step Process](02-8STEP-PROCESS.md)
- [NewsBreif](03-NEWSBRIEF-ARCHITECTURE.md)
- [Cron Design](07-CRON-DESIGN.md)
- [Admin Guide](06-ADMIN-INTERFACE.md)
