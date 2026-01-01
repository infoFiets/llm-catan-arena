# Cost Optimization Analysis - LLM Catan Arena

**Date:** January 1, 2026
**Based on:** Mixed Model Game (376 moves, $1.61 total cost)

---

## Current Token Usage

### Average Tokens per LLM Call
- **Prompt (Input):** 975 tokens
- **Response (Output):** 600 tokens
- **Total:** 1,575 tokens per call

### Current Costs (Claude 3 Haiku)
- **Input cost:** $0.000244 per call (975 tokens @ $0.25/1M)
- **Output cost:** $0.000750 per call (600 tokens @ $1.25/1M)
- **Total cost:** $0.000993 per call

**For a 400-move game:** $0.40
**For a 10-game tournament:** $4.00

---

## Optimization Opportunities

### 📊 Token Reduction Scenarios

| Reduction | New Prompt Size | Savings/Call | Savings/Game | Savings/10 Games |
|-----------|-----------------|--------------|--------------|------------------|
| **20%** | 780 tokens | $0.000049 | **$0.020** | **$0.19** |
| **30%** | 682 tokens | $0.000073 | **$0.029** | **$0.29** |
| **40%** | 585 tokens | $0.000097 | **$0.039** | **$0.39** |
| **50%** | 487 tokens | $0.000122 | **$0.049** | **$0.49** |

---

## 💡 Specific Optimization Techniques

### 1. **Compact State Representation** (-15% tokens)

**Current Format:**
```
Your Resources:
- Wood: 3 pieces
- Brick: 2 pieces
- Sheep: 1 piece
- Wheat: 0 pieces
- Ore: 0 pieces

Your Buildings:
- Settlements: 2 (can build 3 more)
- Cities: 0 (can build 4)
- Roads: 3 (can build 12 more)
```

**Optimized Format:**
```
Resources: W:3 B:2 S:1 Wh:0 O:0
Buildings: Sett:2/5 City:0/4 Road:3/15
```

**Savings:** ~$0.015 per game (~$0.15 per 10 games)

---

### 2. **Action Code Abbreviations** (-10% tokens)

**Current Format:**
```
Available Actions:
1. ActionType.BUILD_SETTLEMENT for RED at coordinate (3, 4)
2. ActionType.BUILD_ROAD for RED from (3, 4) to (4, 4)
3. ActionType.BUY_DEVELOPMENT_CARD for RED
4. ActionType.END_TURN for RED
```

**Optimized Format:**
```
Actions:
1. BS@(3,4)
2. BR:(3,4)→(4,4)
3. BUY_DEV
4. END
```

**Savings:** ~$0.010 per game (~$0.10 per 10 games)

---

### 3. **Abbreviated Opponent Info** (-20% tokens)

**Current Format:**
```
Opponents:
- BLUE: 7 Victory Points, 12 total resources (3 wood, 4 brick, 2 sheep, 2 wheat, 1 ore), 2 settlements, 1 city, 5 roads
- WHITE: 5 Victory Points, 8 total resources, 3 settlements, 0 cities, 4 roads
- ORANGE: 4 Victory Points, 3 total resources, 2 settlements, 0 cities, 3 roads
```

**Optimized Format:**
```
Opp: B:7VP,12c W:5VP,8c O:4VP,3c
```

**Savings:** ~$0.020 per game (~$0.20 per 10 games)

---

### 4. **JSON Format** (-40% tokens) ⭐ BEST OPTION

**Current Format (Natural Language):**
```
Game: Settlers of Catan
Turn: 45
Current Player: RED

Your Resources:
- Wood: 3 pieces
- Brick: 2 pieces
...

[Full verbose descriptions]
```

**Optimized Format (Compact JSON):**
```json
{
  "you": {"res":{"W":3,"B":2,"S":1,"Wh":0,"O":0},"vp":6,"bld":{"s":2,"c":0,"r":3}},
  "opp": [{"c":"B","vp":7,"rc":12},{"c":"W","vp":5,"rc":8},{"c":"O","vp":4,"rc":3}],
  "acts": ["BS@(3,4)","BR:(3,4)→(4,4)","BUY_DEV","END"]
}
```

**Savings:** ~$0.039 per game (~$0.39 per 10 games)

---

## 🎯 Recommended Implementation

### Phase 1: Quick Wins (Easy - Week 1)
✅ **Compact state representation** (-15%)
✅ **Action code abbreviations** (-10%)
**Combined savings:** ~$0.025/game = **$0.25 per 10 games**

### Phase 2: Structural Changes (Medium - Week 2)
✅ **Abbreviated opponent info** (-20%)
**Additional savings:** ~$0.020/game = **$0.20 per 10 games**

### Phase 3: Format Overhaul (Hard - Week 3)
✅ **Full JSON format** (-40%)
**Total savings:** ~$0.039/game = **$0.39 per 10 games**

---

## 📈 Projected Annual Savings

Assuming 1,000 games per year:

| Optimization Level | Token Reduction | Annual Savings (Haiku) | Annual Savings (GPT-4) |
|-------------------|-----------------|------------------------|------------------------|
| **Phase 1** (25%) | 244 tokens | **$25** | **$970** |
| **Phase 2** (45%) | 439 tokens | **$44** | **$1,710** |
| **Phase 3** (40%) | 390 tokens | **$39** | **$1,520** |

*GPT-4 savings are ~39x higher due to higher token costs*

---

## ⚠️ Trade-offs to Consider

### Pros of Compact Formats:
✅ Lower costs (10-40% reduction)
✅ Faster API calls (less data transfer)
✅ More games per API rate limit

### Cons of Compact Formats:
❌ May reduce LLM strategic reasoning quality
❌ Harder to debug (less readable logs)
❌ Requires more prompt engineering testing

---

## 🧪 Recommended Testing Approach

1. **Create optimized prompt builder** (compact version)
2. **Run A/B test:** 10 games standard vs 10 games optimized
3. **Compare:**
   - Win rates
   - Average VP scores
   - Strategic quality (manual review)
   - Cost per game
4. **If quality remains:** Deploy to production
5. **If quality drops:** Fine-tune compression level

---

## 💰 Bottom Line

**For Haiku (most cost-effective model):**
- Current: $0.40 per 400-move game
- Optimized (40% reduction): $0.36 per game
- **Savings: $0.04 per game (10% cost reduction)**

**For GPT-4 Turbo (premium model):**
- Current: ~$1.60 per 400-move game
- Optimized (40% reduction): ~$1.42 per game
- **Savings: $0.18 per game (11% cost reduction)**

**For a 100-game tournament:**
- Haiku savings: **$4.00**
- GPT-4 savings: **$18.00**
- Mixed model savings: **~$8-12.00**

---

## 🚀 Next Steps

1. **Immediate:** Implement Phase 1 optimizations (compact format)
2. **Week 2:** Test and validate quality doesn't degrade
3. **Week 3:** Roll out to all games if successful
4. **Month 2:** Consider JSON format for maximum savings

**Files to modify:**
- `src/prompt_builder.py` - Add `build_compact_prompt()` method
- `src/players/base_player.py` - Add flag for prompt format
- `config.yaml` - Add `use_compact_prompts: true/false`

---

**Generated:** January 1, 2026
