# Why Two-Stage Cron?

Separate fetch from enrich for:
- Reliability (independent failure)
- Speed (fast fetch, slow enrich)
- Flexibility (backlog management)

Stage 1: Fetch & Store (30 min)
Stage 2: Enrich Complete (15 min)
