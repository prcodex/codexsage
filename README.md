# CODEXSAGE - Premium Financial Intelligence System

**Version:** WHITE1.0 COMPLETE  
**Date:** November 3, 2025  
**Status:** Production Ready ✅

## 🎯 What is CODEXSAGE?

Complete email intelligence system that transforms premium financial newsletters into an organized, enriched, searchable feed with AI-powered analysis.

### Key Features
- ✅ **21 Enrichment Handlers** - Specialized AI processing for each source
- ✅ **NewsBreif Story Splitting** - Digest emails → Individual story cards  
- ✅ **Option C Keyword Extraction** - Smart filtering with 89 exclusion terms
- ✅ **HTML Email Popup** - Beautiful fallback for stories without links
- ✅ **Admin Interface** - Visual management of all configurations
- ✅ **White Twitter Interface** - Clean, modern card-based display
- ✅ **Bilingual Support** - English + Portuguese
- ✅ **Show More/Less Cards** - Collapsible design for efficient scanning

---

## 🚀 Quick Start

```bash
# 1. Clone repository
git clone https://github.com/prcodex/codexsage.git
cd codexsage

# 2. Install dependencies
pip install -r deployment/requirements.txt

# 3. Configure environment
cp config/env.example .env
# Edit .env with your credentials

# 4. Create database
cd src/scripts
./recreate_database.sh

# 5. Start services
cd ../main
python3 sage4_interface_fixed.py &    # Main interface (8540)
python3 scrapex_admin.py &             # Admin interface (8543)
```

**Access:**
- Main Interface: http://localhost:8540
- Admin Interface: http://localhost:8543

---

## 📚 Documentation

### Core Concepts
- [📖 System Overview](docs/00-OVERVIEW.md) - What SAGE does and why
- [🏗️ Architecture](docs/01-ARCHITECTURE.md) - Technical components
- [📋 8-Step Process](docs/02-8STEP-PROCESS.md) - **Complete processing pipeline**
- [📰 NewsBreif Architecture](docs/03-NEWSBRIEF-ARCHITECTURE.md) - Story splitting explained

### Implementation Guides
- [🔑 Keyword Extraction](docs/04-KEYWORD-EXTRACTION.md) - Option C hybrid approach
- [🎨 Handlers Guide](docs/05-HANDLERS-GUIDE.md) - All 21 handlers documented
- [🎛️ Admin Interface](docs/06-ADMIN-INTERFACE.md) - Visual management guide
- [⏰ Cron Design](docs/07-CRON-DESIGN.md) - **Two-stage automation architecture**

### Reference
- [💾 Database Schema](docs/08-DATABASE-SCHEMA.md) - LanceDB structure
- [🔧 Troubleshooting](docs/09-TROUBLESHOOTING.md) - Common issues & solutions

---

## 🧠 Knowledge Base

Complete history of system development:

### Conversations
- [Oct 31-Nov 3: Complete Build](knowledge-base/conversations/2025-11-01-03-complete-build.md)
- Daily summaries of all implementation work

### Design Decisions
- [Why NewsBreif Splitting?](knowledge-base/decisions/why-newsbrief-splitting.md)
- [Why Option C Keywords?](knowledge-base/decisions/why-option-c-keywords.md)
- [Why Two-Stage Cron?](knowledge-base/decisions/two-stage-vs-single-cron.md)
- [Why White Interface?](knowledge-base/decisions/why-white-interface.md)

### Problems Solved
- Browser caching issues
- Link extraction accuracy
- Generic keyword filtering
- Portuguese NewsBreif support

---

## 🏗️ System Architecture

```
Gmail IMAP
    ↓
FETCH → FILTER → TAG → STORE
    ↓
LanceDB on S3
    ↓
MAP → ENRICH → KEYWORDS → SAVE
    ↓
Display (Port 8540)
```

**Two-Stage Automation:**
- **Cron 1:** Fetch & Store (Steps 1-4) - Every 30 min
- **Cron 2:** Enrich Complete (Steps 5-8) - Every 15 min

---

## 💰 Cost

**Per Email:**
- NewsBreif: $0.015 (enrichment) + $0.006 (keywords for 6 stories) = **$0.021**
- Gold Standard: $0.024 (deep analysis) + $0.001 (keywords) = **$0.025**
- Simple handlers: $0.002-$0.005

**Monthly (10 digests/day):**
- Processing: ~$6.30
- Storage (S3): ~$0.50
- **Total: ~$7/month**

---

## 🎨 Screenshots

### Main Interface (8540)
- White Twitter-style cards
- Show More/Less buttons
- Keywords badges (🔑)
- HTML email popup
- Load More pagination

### Admin Interface (8543)
- 📬 Allowed Senders (22 groups, edit popup)
- 🏷️ Detection Rules (16 rules, edit popup)
- 📊 Tag Mappings (41 mappings)
- 🚫 Keyword Exclusions (89 terms, 7 categories)

---

## 🔧 Components

### Main System (Port 8540)
- **sage4_interface_fixed.py** - Flask app serving enriched feed
- **sage_4.0_interface.html** - White Twitter UI with Show More/Less
- **unified_adaptive_enrichment.py** - Orchestrates 21 handlers
- **keyword_extractor.py** - Option C hybrid extraction

### Admin System (Port 8543)
- **scrapex_admin.py** - Flask app for visual configuration
- **admin_complete.html** - 4-tab interface with edit popups

### Handlers (21 total)
- NewsBreif (Bloomberg, WSJ, Reuters, Barron's, FT)
- Gold Standard Enhanced (Goldman Sachs, research)
- Itau Daily (Portuguese + English)
- Javier Blas, Cochrane, WSJ Opinion, Bloomberg Breaking
- ...and more

---

## 📊 Current System Stats

- **Database:** 39 items (37 NewsBreif stories + 2 emails)
- **Enrichment:** 100% coverage
- **Keywords:** 100% (4-6 specific terms each)
- **Real Links:** 49% (smart matching)
- **HTML Popup:** 51% (fallback)

---

## 🚀 Next Steps

### For Users
1. Review documentation in `docs/`
2. Understand 8-step process
3. Configure your senders and rules
4. Run database recreation
5. Start using the system

### For Developers
1. Study handler architecture
2. Review NewsBreif splitting logic
3. Understand keyword extraction (Option C)
4. Implement two-stage cron (see docs/07-CRON-DESIGN.md)
5. Extend with new handlers

---

## 📖 Learning Path

1. **Start Here:** [System Overview](docs/00-OVERVIEW.md)
2. **Understand Flow:** [8-Step Process](docs/02-8STEP-PROCESS.md)
3. **Deep Dive:** [NewsBreif Architecture](docs/03-NEWSBRIEF-ARCHITECTURE.md)
4. **Automation:** [Cron Design](docs/07-CRON-DESIGN.md)
5. **Customize:** [Admin Interface Guide](docs/06-ADMIN-INTERFACE.md)

---

## 🤝 Contributing

This repository serves as both:
- **Working System** - Ready to deploy
- **Knowledge Base** - Complete documentation of decisions

See `knowledge-base/` for conversation history and design rationale.

---

## 📝 License

Private repository for Pedro Ribeiro's SAGE system.

---

## 🎉 Achievements

- Complete 8-step processing pipeline
- 21 specialized enrichment handlers
- NewsBreif story splitting (1 digest → 6 cards)
- Option C keyword extraction (no generic terms)
- Full visual admin interface
- Bilingual support (EN/PT)
- HTML popup fallback
- 49% link extraction accuracy

**Ready for production deployment and automation!**

---

**For complete documentation, see [docs/](docs/) directory.**
