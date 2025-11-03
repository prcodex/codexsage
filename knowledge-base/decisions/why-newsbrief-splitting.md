# Why Split NewsBreif Digests?

## The Problem
Bloomberg Morning Briefing contains 6-12 separate news stories in ONE email.

Displaying as one card:
- ❌ Massive wall of text (3,000+ chars)
- ❌ Hard to scan and find stories
- ❌ Can't link individual stories
- ❌ One set of keywords for all stories

## The Solution
Split the digest into individual story entries.

## Benefits
- ✅ Easy to scan (6 cards vs 1)
- ✅ Individual story links
- ✅ Keywords per story (more specific)
- ✅ Better mobile experience

## Cost Analysis
- One AI call extracts all stories: $0.015
- Splitting is text parsing: Free
- Keywords per story: $0.001 × 6 = $0.006
- **Total: $0.021 per digest**

vs.

- Split first, enrich each: $0.015 × 6 = $0.09
- **Savings: 77%!**

## Architecture Decision
**Enrich first, THEN split** for maximum efficiency.
