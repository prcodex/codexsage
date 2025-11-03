# Configuration Files

## Overview
This directory contains all configuration files for the SAGE system.

## Files

### allowed_senders.json
**Purpose:** Whitelist of email senders allowed to be processed

**Structure:**
```json
[
  {
    "sender_tag": "Goldman Sachs",
    "email_patterns": ["goldmansachs.com", "gs.com"],
    "description": "Investment bank research",
    "active": true
  }
]
```

**Current:** 22 sender groups configured

### tag_detection_rules.json
**Purpose:** Rules for assigning sender tags based on email content

**Structure:**
```json
{
  "WSJ Opinion": {
    "sender": "Wall Street Journal",
    "subject_contains": "Opinion:",
    "body_contains": "",
    "logic": "AND",
    "description": "WSJ Opinion articles"
  }
}
```

**Current:** 16 tagging rules configured

### tag_handler_mappings.json
**Purpose:** Maps sender tags to enrichment handlers

**Structure:**
```json
{
  "bloomberg": "newsbrief",
  "goldman_sachs": "gold_standard",
  "wsj_opinion": "wsj_opinion_teaser"
}
```

**Current:** 41 tag-to-handler mappings

### keyword_exclusions.json
**Purpose:** Generic terms to exclude from keyword extraction

**Structure:**
```json
{
  "meta_descriptions_en": ["Breaking News", "Analysis"],
  "meta_descriptions_pt": ["Notícias", "Análise"]
}
```

**Current:** 89 exclusion terms in 7 categories

### env.example
**Purpose:** Template for environment variables

**Usage:**
```bash
cp env.example .env
# Edit .env with your actual credentials
source .env
```

## Managing Configuration

### Via Admin Interface (Recommended)
http://localhost:8543/
- Edit allowed senders visually
- Edit tagging rules visually
- Manage keyword exclusions

### Via JSON Files (Advanced)
Edit files directly, then restart services:
```bash
pkill -f sage4_interface
pkill -f scrapex_admin
python3 src/main/sage4_interface_fixed.py &
python3 src/main/scrapex_admin.py &
```

## Security
⚠️ Never commit .env file with actual credentials!
⚠️ Use env.example as template only
