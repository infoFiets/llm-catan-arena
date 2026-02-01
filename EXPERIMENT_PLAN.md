# LLM Catan Arena - Full Tournament Plan

## Overview

Tournament to rank 48 LLM models by their Settlers of Catan playing ability using Elo ratings.

## Tournament Math

| Metric | Value |
|--------|-------|
| Total models | 48 |
| Unique model pairs | C(48,2) = 1,128 |
| Pairs per 4-player game | C(4,2) = 6 |
| Min games for 1x pair coverage | 188 games |
| Target games per model | 20-30 |
| Min total games | 240+ |

## Current Settings

| Setting | Value | Notes |
|---------|-------|-------|
| Config file | `config_full_tournament.yaml` | 48 models |
| Victory Points | 8 VP | Faster than standard 10 VP |
| Max Turns | 200 | ~50 rounds per game |
| Format | TOON | ~23% cheaper per turn than JSON |

---

## Pre-Tournament Setup

```bash
# 1. Activate environment
source venv/bin/activate

# 2. Reset Elo ratings for clean start
python scripts/elo_ratings.py --reset

# 3. Verify config has all models
python scripts/generate_matchups.py --config config_full_tournament.yaml --games 0 --stats
```

---

## Tournament Batches

Run the tournament in batches, checking progress after each.

### Batch 1: Initial Sample (50 games)

**Goal:** Get initial data on all models, verify everything works.

```bash
# Run 50 games with balanced matchups
python scripts/run_batch.py --config config_full_tournament.yaml --games 50

# Or generate matchups first and run manually:
python scripts/generate_matchups.py --games 50 --format list --stats
```

**Checkpoint 1:** After 50 games
```bash
python scripts/tournament_stats.py
```

**What to check:**
- [ ] Are all 48 models appearing in games? (should see ~4 games each)
- [ ] Any errors or models failing consistently?
- [ ] Rough cost estimate per game?

---

### Batch 2: Build Coverage (50 more games → 100 total)

**Goal:** Increase pair coverage, start seeing ranking patterns.

```bash
python scripts/run_batch.py --config config_full_tournament.yaml --games 50
```

**Checkpoint 2:** After 100 games
```bash
python scripts/tournament_stats.py
```

**What to check:**
- [ ] Each model has 8+ games
- [ ] Pair coverage > 25%
- [ ] Any clear leaders/laggards emerging?
- [ ] Average CI width (target: < 150 points)

---

### Batch 3: Statistical Significance (50 more games → 150 total)

**Goal:** Tighten confidence intervals, establish ranking tiers.

```bash
python scripts/run_batch.py --config config_full_tournament.yaml --games 50
```

**Checkpoint 3:** After 150 games
```bash
python scripts/tournament_stats.py
```

**What to check:**
- [ ] Each model has 12+ games
- [ ] Pair coverage > 40%
- [ ] Top 5 and bottom 5 have non-overlapping CIs?
- [ ] Average CI width < 120 points

---

### Batch 4: Full Coverage (50 more games → 200 total)

**Goal:** Ensure all pairs have met at least once.

```bash
python scripts/run_batch.py --config config_full_tournament.yaml --games 50
```

**Checkpoint 4:** After 200 games
```bash
python scripts/tournament_stats.py
```

**What to check:**
- [ ] Each model has 16+ games
- [ ] Pair coverage > 50%
- [ ] Most adjacent rankings are statistically distinguishable
- [ ] Rankings stable compared to Checkpoint 3?

---

### Batch 5+: Refinement (until stable)

**Goal:** Continue until rankings stabilize.

Run additional batches of 25-50 games until:
- Pair coverage > 75%
- Average CI width < 100 points
- Top 10 rankings unchanged for 2 consecutive batches

```bash
# Run smaller batches for fine-tuning
python scripts/run_batch.py --config config_full_tournament.yaml --games 25
python scripts/tournament_stats.py
```

---

## Quick Reference Commands

### Check Current Standings
```bash
python scripts/tournament_stats.py
```

### Check Elo Leaderboard (alternative)
```bash
python scripts/elo_ratings.py --min-games 5
```

### View Recent Games
```bash
python scripts/elo_ratings.py --history 20
```

### Generate Matchups Without Running
```bash
# See what matchups would be generated
python scripts/generate_matchups.py --games 20 --format list --stats
```

### Run Specific Matchup Manually
```bash
python scripts/run_tournament.py \
  --single-game claude-4.5-sonnet gpt-5.2 gemini-2.5-pro llama-4-maverick \
  --mode text --format toon --games 1 \
  --config config_full_tournament.yaml
```

### Emergency Stop
- **Ctrl+C once** = End current game early, save results based on current VP
- **Ctrl+C twice** = Force quit without saving

---

## Cost Estimates

Based on Phase 1 testing (~$0.15-0.20 per game for budget models):

| Batch | Games | Estimated Cost |
|-------|-------|----------------|
| 1 | 50 | ~$10-15 |
| 2 | 50 | ~$10-15 |
| 3 | 50 | ~$10-15 |
| 4 | 50 | ~$10-15 |
| Total (200) | 200 | ~$40-60 |

**Note:** Premium models (claude-opus, gpt-5.2) cost more. Actual costs depend on game length.

---

## Progress Tracking

### Batch Status
- [ ] Batch 1 complete (50 games)
- [ ] Checkpoint 1 reviewed
- [ ] Batch 2 complete (100 games)
- [ ] Checkpoint 2 reviewed
- [ ] Batch 3 complete (150 games)
- [ ] Checkpoint 3 reviewed
- [ ] Batch 4 complete (200 games)
- [ ] Checkpoint 4 reviewed
- [ ] Rankings stable - tournament complete

### Key Metrics to Track

| Checkpoint | Games | Models w/ 10+ games | Pair Coverage | Avg CI Width |
|------------|-------|---------------------|---------------|--------------|
| 1 | 50 | ? | ?% | ? |
| 2 | 100 | ? | ?% | ? |
| 3 | 150 | ? | ?% | ? |
| 4 | 200 | ? | ?% | ? |

---

## Model Categories

For analysis, models are grouped by:

- **Flagship**: claude-4.5-opus, gpt-5.2, gemini-3-pro, etc.
- **Fast/Cheap**: haiku, gpt-5-mini, gemini-flash, etc.
- **Open Source**: llama, deepseek, qwen, mixtral
- **Reasoning**: claude-3.7-thinking, deepseek-r1, qwen-thinking

See `config_full_tournament.yaml` for full category definitions.

---

## Post-Tournament Analysis

After tournament completion:

1. **Final leaderboard** with confidence intervals
2. **Provider comparison**: Anthropic vs OpenAI vs Google vs Meta vs Others
3. **Cost-effectiveness**: Elo per dollar spent
4. **Generation comparison**: How did model generations improve?
5. **Category analysis**: Flagship vs budget vs reasoning models

```bash
# Generate final analysis (TODO: create this script)
python scripts/analyze_tournament.py --final
```
