# Why Two-Stage Cron Instead of Single Job?

## Decision
Separate cron jobs for fetch (Stage 1) vs enrich (Stage 2).

## Rationale

### Reliability
- If enrichment fails, fetch still works
- Can manually fix enrichment without re-fetching
- Independent error handling

### Speed
- Fetch completes in 1-2 min (no AI)
- Don't block new fetches while enriching
- Can see raw emails immediately

### Flexibility
- Enrich can run more frequently (15 min vs 30 min)
- Can catch up on backlog faster
- Can enrich old emails anytime

### NewsBreif Integration
- Splitting fits naturally in Stage 2
- No separate cron needed
- Clean architecture

## Alternative Considered
Single cron doing everything.

**Rejected because:**
- Slow (must wait for AI)
- Less reliable (one failure breaks all)
- Can't manage backlog independently
