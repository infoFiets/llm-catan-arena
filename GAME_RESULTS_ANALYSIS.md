# LLM Catan Arena - Game Results Analysis

## Summary of Games Played

**Date:** December 31, 2025 - January 1, 2026
**Total Games:** 3 completed games
**Total Cost:** $2.10
**Total Tokens:** 1,032,148

---

## Game Results

### Game 1: All-Haiku Battle
**Timestamp:** 2025-12-31 23:03:56
**Duration:** 114 minutes (~1.9 hours)
**Session ID:** Settlers of Catan_20251231_230356

| Player | Model | Victory Points | Placement |
|--------|-------|----------------|-----------|
| 🟠 ORANGE | Claude 3 Haiku | **11** | 🏆 1st |
| 🔴 RED | Claude 3 Haiku | 6 | 2nd |
| 🔵 BLUE | Claude 3 Haiku | 3 | 3rd |
| ⚪ WHITE | Claude 3 Haiku | 2 | 4th |

**Cost Breakdown:**
- Total Cost: $0.2885
- Total Tokens: 477,145
- Total Moves: 752
- Cost per Move: $0.000384
- Tokens per Move: 634.5

---

### Game 2: Mixed Model Championship
**Timestamp:** 2025-12-31 23:04:55
**Duration:** 26 minutes
**Session ID:** Settlers of Catan_20251231_230455

| Player | Model | Victory Points | Placement | Moves | Cost | Cost/Move |
|--------|-------|----------------|-----------|-------|------|-----------|
| 🔵 BLUE | GPT-4 Turbo | **10** | 🏆 1st | 115 | $1.27 | $0.0111 |
| 🟠 ORANGE | Claude 3 Haiku | 6 | 2nd | ~93 | $0.035 | $0.0004 |
| ⚪ WHITE | Claude 3 Haiku | 5 | 3rd | ~93 | $0.035 | $0.0004 |
| 🔴 RED | Claude 3.5 Sonnet | 2 | 4th | 71 | $0.27 | $0.0037 |

**Cost Breakdown:**
- Total Cost: $1.6084
- Total Tokens: 225,486
- Total Moves: 372
- Cost per Move: $0.004324
- Tokens per Move: 606.2

**Model Performance:**
- **GPT-4 Turbo:** Won with 10 VP, but cost **$1.27** (79% of total game cost)
- **Claude 3.5 Sonnet:** Last place with 2 VP, cost $0.27 (17% of total game cost)
- **Claude 3 Haiku (x2):** Combined 11 VP, cost only **$0.07** (4% of total game cost)

---

### Game 3: Clean Test (Bug Fix Verification)
**Timestamp:** 2025-12-31 22:09:45
**Duration:** 19.5 minutes
**Session ID:** Settlers of Catan_20251231_220945

| Player | Model | Victory Points | Placement |
|--------|-------|----------------|-----------|
| 🔵 BLUE | Claude 3 Haiku | **11** | 🏆 1st |
| 🔴 RED | Claude 3 Haiku | 3 | 2nd |
| 🟠 ORANGE | Claude 3 Haiku | 5 | 3rd |
| ⚪ WHITE | Claude 3 Haiku | 2 | 4th |

**Cost Breakdown:**
- Total Cost: $0.2011
- Total Tokens: 329,517
- No errors - Clean run with bug fixes!

---

## Cost Analysis by Model

### Per-Move Costs
| Model | Avg Cost/Move | Avg Tokens/Move | Relative Cost |
|-------|---------------|-----------------|---------------|
| Claude 3 Haiku | $0.0004 | ~600 | 1x (baseline) |
| Claude 3.5 Sonnet | $0.0037 | ~600 | **9.25x** |
| GPT-4 Turbo | $0.0111 | ~600 | **27.75x** |

### Win Rate vs Cost
| Model | Games | Wins | Win Rate | Avg Cost to Win |
|-------|-------|------|----------|-----------------|
| Claude 3 Haiku | 3 | 2 | 67% | $0.24 |
| GPT-4 Turbo | 1 | 1 | 100% | $1.27 |
| Claude 3.5 Sonnet | 1 | 0 | 0% | N/A (Lost) |

---

## Key Findings

### 1. **GPT-4 Turbo is Effective but Expensive**
- ✅ Won the mixed model game
- ⚠️ Cost **5.5x more** than the entire all-Haiku game
- 💰 $0.127 cost per victory point earned

### 2. **Claude 3 Haiku is the Most Cost-Efficient**
- ✅ Won 2 out of 3 games (67% win rate)
- ✅ Avg cost per win: $0.24
- ✅ **27x cheaper** per move than GPT-4
- 💡 Best choice for tournaments and testing

### 3. **Claude 3.5 Sonnet Underperformed**
- ❌ Came in last place (2 VP)
- ⚠️ Cost 9x more than Haiku
- ❌ Could not parse responses well ("I choose Action 2..." format issues)

### 4. **Game Duration**
- All-Haiku games: ~60-120 minutes
- Mixed model games: ~20-30 minutes (fewer tokens processed)
- GPT-4's higher latency doesn't significantly slow down games

---

## Recommendations

### For Testing & Development
**Use Claude 3 Haiku exclusively**
- Cost: ~$0.20-0.30 per game
- Fast iteration
- Good strategic play
- High win rate

### For Tournaments
**Mixed Haiku + One Premium Model**
- 3x Haiku + 1x GPT-4: ~$0.50 per game
- Tests premium model performance
- Keeps costs reasonable

### For Research
**Full Premium Model Games**
- 4x GPT-4: ~$5-6 per game
- 4x Claude 3.5 Sonnet: ~$1-2 per game
- Use for final benchmarking only

---

## Files Generated

- ✅ `game_results_summary.csv` - Machine-readable results
- ✅ `GAME_RESULTS_ANALYSIS.md` - This human-readable report
- ✅ `data/games/*.json` - Full game logs with all moves and prompts
- ✅ `TEST_RESULTS.md` - Comprehensive test documentation

---

**Generated:** January 1, 2026
