# Admin Interface Guide

**Complete guide to visual configuration management (Port 8543)**

---

## Overview

The Admin Interface provides visual management of all SAGE configurations:
- 📬 **Allowed Senders** (22 groups)
- 🏷️ **Detection Rules** (16 tagging rules)
- 📊 **Tag Mappings** (41 tag→handler assignments)
- 🚫 **Keyword Exclusions** (89 terms, 7 categories)

**Access:** http://localhost:8543/

⚠️ **IMPORTANT:** Always use **Incognito mode** due to aggressive browser caching!

---

## Tab 1: 📬 Allowed Senders

### Purpose
Manage which email senders are allowed to be processed.

### Display
22 sender groups shown as cards:
```
┌──────────────────────────────────────┐
│ Goldman Sachs                         │
│ Investment bank research and analysis │
│                                       │
│ [goldmansachs.com] [gs.com]          │
│ [janhatzius@gs.com]                  │
│                                       │
│ [✏️ Edit] [🗑️ Delete]                 │
└──────────────────────────────────────┘
```

### Edit Sender Popup

Click [✏️ Edit] to open:
```
┌──────────────────────────────────────┐
│ ✏️ Edit Sender: Goldman Sachs         │
├──────────────────────────────────────┤
│ Sender Name:                         │
│ [Goldman Sachs]                      │
│                                      │
│ Email Patterns (one per line):      │
│ ┌────────────────────────┐          │
│ │ goldmansachs.com       │          │
│ │ gs.com                 │          │
│ │ janhatzius@gs.com      │          │
│ └────────────────────────┘          │
│ 💡 Examples: bloomberg.com |         │
│    specific@email.com                │
│                                      │
│ Description:                         │
│ [Investment bank research...]        │
│                                      │
│      [Cancel] [💾 Save Changes]      │
└──────────────────────────────────────┘
```

**Features:**
- Pre-filled with current data
- Multi-line pattern editor
- Validation (name & patterns required)
- Save preview

**Current Status:** Shows preview, actual save coming soon

---

## Tab 2: 🏷️ Detection Rules

### Purpose
Manage how emails are tagged based on sender/subject/body.

### Display
16 tagging rules shown as cards:
```
┌──────────────────────────────────────┐
│ WSJ Opinion                           │
├──────────────────────────────────────┤
│ From: Wall Street Journal            │
│ Subject contains: "Opinion:"         │
│ Logic: AND                           │
│                                      │
│ WSJ Opinion articles - subject must  │
│ contain 'Opinion:'                   │
│                                      │
│ [✏️ Edit] [🗑️ Delete]                 │
└──────────────────────────────────────┘
```

### Edit Rule Popup

Click [✏️ Edit] to open:
```
┌──────────────────────────────────────┐
│ ✏️ Edit Tagging Rule: WSJ Opinion     │
├──────────────────────────────────────┤
│ Tag Name:                            │
│ [WSJ Opinion]                        │
│                                      │
│ Sender (Sender Name):                │
│ [▼ Wall Street Journal] ← Dropdown  │
│    (22 senders available)            │
│                                      │
│ Subject Contains:                    │
│ [Opinion:]                           │
│ 💡 Optional: Text in subject         │
│                                      │
│ Body Contains:                       │
│ []                                   │
│ 💡 Optional: Text in body            │
│                                      │
│ Logic:                               │
│ [▼ AND (all must match)]             │
│                                      │
│ Description:                         │
│ [WSJ Opinion articles...]            │
│                                      │
│ 💡 How This Works:                   │
│ • Sender: Matches Sender Name        │
│ • Subject/Body: Optional patterns    │
│ • AND: All filled conditions match   │
│ • OR: Any filled condition matches   │
│                                      │
│      [Cancel] [💾 Save Rule]         │
└──────────────────────────────────────┘
```

**Features:**
- Pre-filled with current rule
- Sender dropdown (from Allowed Senders)
- AND/OR logic selector
- Help text explaining logic
- Validation

**Current Status:** Shows preview, actual save coming soon

---

## Tab 3: 📊 Tag Mappings

### Purpose
View how sender tags map to enrichment handlers.

### Display
Table with 41 mappings:

| Tag | Handler | Handler Type |
|-----|---------|--------------|
| bloomberg | newsbrief | 📰 NewsBreif |
| goldman_sachs | gold_standard | ⭐ Gold Standard |
| wsj_opinion | wsj_opinion_teaser | 📄 Special |
| itau | itau_daily | 📊 Itau Daily |

**Current Status:** Read-only (no editing yet)

---

## Tab 4: 🚫 Keyword Exclusions

### Purpose
Manage generic terms to exclude from keyword extraction.

### Display
7 categories with 89 terms total:
```
┌──────────────────────────────────────┐
│ 📰 Meta Descriptions (English)        │
├──────────────────────────────────────┤
│ [Breaking News ×] [Analysis ×]       │
│ [Market Updates ×] [Report ×]        │
│ [Outlook ×] [Summary ×] ...          │
│                                      │
│ [➕ Add to this category]            │
└──────────────────────────────────────┘

┌──────────────────────────────────────┐
│ 📰 Meta Descriptions (Portuguese)     │
├──────────────────────────────────────┤
│ [Notícias ×] [Análise ×]             │
│ [Resumo ×] [Relatório ×] ...         │
│                                      │
│ [➕ Add to this category]            │
└──────────────────────────────────────┘

... 5 more categories
```

### Add Term
1. Click [➕ Add to this category]
2. Enter term (e.g., "Headlines")
3. Saves automatically
4. Next enrichment uses updated list

### Remove Term
1. Click [×] on any term badge
2. Confirm removal
3. Saves automatically

**Current Status:** FULLY WORKING ✅

---

## Browser Caching Issues

### The Problem
Admin interface uses heavy JavaScript. Browsers cache aggressively.

### Symptoms
- Edit buttons show "coming soon" even after fix
- New terms don't appear
- Changes don't persist
- Old UI shows instead of new

### Solution

**Always use Incognito Mode:**
```
Chrome/Edge: Ctrl+Shift+N
Firefox: Ctrl+Shift+P
Safari: Cmd+Shift+N
```

**Or Hard Refresh:**
```
Chrome/Firefox: Ctrl+Shift+R
Safari: Cmd+Shift+R
```

**Or Clear Cache:**
```
Chrome: Ctrl+Shift+Delete
Select "Cached images and files"
Click "Clear data"
```

---

## API Endpoints

### GET /api/allowed_senders_full
Returns all sender groups:
```json
{
  "senders": [
    {
      "sender_tag": "Goldman Sachs",
      "email_patterns": ["goldmansachs.com", "gs.com"],
      "description": "Investment bank research",
      "active": true
    }
  ]
}
```

### GET /api/detection_rules
Returns all tagging rules:
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

### GET /api/tag_mappings_data
Returns tag→handler mappings:
```json
{
  "bloomberg": "newsbrief",
  "goldman_sachs": "gold_standard"
}
```

### GET /api/keyword_exclusions
Returns exclusion list:
```json
{
  "meta_descriptions_en": ["Breaking News", "Analysis"],
  "meta_descriptions_pt": ["Notícias", "Análise"]
}
```

### POST /api/keyword_exclusions
Saves updated exclusion list.

---

## Troubleshooting

### Problem: Tabs not switching
**Solution:** Hard refresh (Ctrl+Shift+R)

### Problem: Edit buttons show "coming soon"
**Solution:** Use Incognito mode (browser cache)

### Problem: Changes don't save
**Solution:** Check console (F12) for errors

### Problem: Senders not loading
**Solution:** Check `/api/allowed_senders_full` in browser

---

## Future Enhancements

### Planned Features
- ✅ Edit sender (preview working, save coming)
- ✅ Edit rule (preview working, save coming)
- ⏳ Delete sender
- ⏳ Add new sender via UI
- ⏳ Delete rule
- ⏳ Create new rule via visual builder
- ⏳ Edit tag mappings
- ⏳ Bulk import/export

---

**The admin interface provides essential visual management, reducing configuration errors and making the system accessible to non-technical users.**
