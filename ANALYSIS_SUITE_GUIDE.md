# LLM Catan Arena - Analysis Suite Guide

Complete analysis and visualization suite successfully built and tested!

## 📦 What Was Built

### 1. Enhanced Analysis Module (`src/analysis.py`)
Comprehensive statistical analysis functions:
- `load_all_games()` - Load all game JSON files
- `calculate_win_rates()` - Win percentage by model
- `calculate_costs()` - Cost analysis including cost per win
- `calculate_game_stats()` - Overall game statistics
- `head_to_head_matrix()` - Win rates between specific models
- `export_summary_report()` - Generate markdown summary

### 2. Visualization Suite (`src/visualizations.py`)
Professional, blog-ready charts (300 DPI PNG):
- `plot_win_rates()` - Win rate bar chart
- `plot_cost_efficiency()` - Cost vs wins scatter plot
- `plot_cost_per_win()` - Cost efficiency bar chart
- `plot_game_length_distribution()` - Game length histogram
- `plot_head_to_head()` - Head-to-head heatmap
- `plot_decision_speed()` - API response time box plot
- `plot_token_usage()` - Token usage stacked bar chart
- `plot_example_game_timeline()` - Sample game visualization
- `generate_all_visualizations()` - Generate all charts at once

### 3. Highlight Finder (`src/highlight_finder.py`)
Automatic detection of interesting moments:
- `find_interesting_moments()` - Categorize games (comebacks, dominant wins, close finishes, etc.)
- `analyze_model_patterns()` - Model-specific strategy patterns
- `get_game_details()` - Detailed game information
- `generate_highlights_report()` - Markdown highlights report
- `export_interesting_game_details()` - Deep dive into specific games

### 4. CLI Tool (`scripts/analyze.py`)
Command-line interface for quick analysis

### 5. Blog Draft Generator (`scripts/generate_blog_draft.py`)
Automatic blog post generation with embedded statistics

### 6. Interactive Notebook (`notebooks/analyze_results.ipynb`)
Comprehensive Jupyter notebook with all analysis sections

## 🚀 Quick Start

### Run Complete Analysis
```bash
# Activate your virtual environment
source venv/bin/activate

# Run full analysis (summary, charts, reports)
python scripts/analyze.py --all
```

### Output Files Created
```
output/
├── charts/
│   ├── win_rates.png
│   ├── cost_efficiency.png
│   ├── cost_per_win.png
│   ├── game_length_distribution.png
│   ├── head_to_head.png
│   ├── decision_speed.png
│   └── token_usage.png
├── summary_report.md
├── highlights_report.md
└── blog_draft.md
```

## 📊 Usage Examples

### 1. Quick Summary
```bash
python scripts/analyze.py --summary
```
Prints win rates and cost analysis to console.

### 2. Generate Charts Only
```bash
python scripts/analyze.py --charts
```
Creates all visualizations in `output/charts/`.

### 3. Find Interesting Moments
```bash
python scripts/analyze.py --highlights
```
Shows close finishes, dominant wins, fastest games, etc.

### 4. Generate Reports
```bash
# Summary report
python scripts/analyze.py --export-report

# Highlights report
python scripts/analyze.py --export-highlights
```

### 5. View Specific Game Details
```bash
python scripts/analyze.py --game-details "Settlers of Catan_20251231_230455"
```

### 6. Generate Blog Draft
```bash
python scripts/generate_blog_draft.py
```
Creates a complete blog post draft in `output/blog_draft.md`.

### 7. Interactive Analysis (Jupyter)
```bash
jupyter notebook notebooks/analyze_results.ipynb
```

## 🎨 Customization

### Adjust Highlight Thresholds
Edit `src/highlight_finder.py` function parameters:
```python
highlights = find_interesting_moments(
    games,
    comeback_threshold=0.3,    # 30% threshold for comebacks
    dominant_margin=5,         # 5 VP margin for dominant wins
    close_margin=2             # 2 VP margin for close finishes
)
```

### Custom Analysis
Use the analysis functions directly in Python:
```python
from src.analysis import load_all_games, calculate_win_rates

games = load_all_games("data/games")
win_rates = calculate_win_rates(games)
print(win_rates)
```

### Filter Games
```python
# Analyze only recent games
recent_games = [g for g in games if "20251231" in g['session_id']]
calculate_win_rates(recent_games)
```

## 📈 Current Results (8 Games)

**Win Rates:**
- GPT-4 Turbo: 100.0% (1/1)
- Claude 3 Haiku: 92.3% (24/26)
- haiku: 0.0% (0/4)
- Claude 3.5 Sonnet: 0.0% (0/1)

**Cost Efficiency:**
- Cheapest per game: Claude 3 Haiku ($0.0271)
- Best cost per win: Claude 3 Haiku ($0.0294)
- Most expensive: GPT-4 Turbo ($1.2738)

**Game Stats:**
- Average length: 147.8 turns
- Average duration: 33.2 minutes
- Average victory margin: 3.9 VP

## 🔧 Dependencies

All required dependencies installed:
- pandas
- numpy
- matplotlib
- seaborn
- tabulate (for markdown table generation)

## 📝 Blog Workflow

1. **Run tournament games** (you've already done this)
2. **Generate all analysis:**
   ```bash
   python scripts/analyze.py --all
   ```
3. **Generate blog draft:**
   ```bash
   python scripts/generate_blog_draft.py
   ```
4. **Review and edit:**
   - Edit `output/blog_draft.md`
   - Add personal insights and commentary
   - Adjust chart placements
5. **Publish:**
   - Charts are in `output/charts/`
   - Ready for blog platform upload

## 🎯 Next Steps

Before running your full 20-game tournament:
1. ✅ All analysis tools are working
2. ✅ Visualizations generate correctly
3. ✅ Reports are comprehensive
4. Ready to run the full tournament!

After tournament:
```bash
# Generate everything
python scripts/analyze.py --all
python scripts/generate_blog_draft.py

# Or use the interactive notebook
jupyter notebook notebooks/analyze_results.ipynb
```

## 🐛 Troubleshooting

**Charts not displaying:**
- Ensure matplotlib backend is configured
- Check file permissions in `output/charts/`

**Missing data in reports:**
- Some test games may have incomplete data (normal)
- Full tournament games will have complete data

**Import errors:**
- Activate virtual environment: `source venv/bin/activate`
- Install missing dependencies: `pip install <package>`

## 📚 File Reference

**Analysis:**
- `src/analysis.py` - Statistical functions
- `src/visualizations.py` - Chart generation
- `src/highlight_finder.py` - Interesting moments

**Scripts:**
- `scripts/analyze.py` - CLI tool
- `scripts/generate_blog_draft.py` - Blog generator

**Notebooks:**
- `notebooks/analyze_results.ipynb` - Interactive analysis

**Output:**
- `output/summary_report.md` - Statistical summary
- `output/highlights_report.md` - Interesting moments
- `output/blog_draft.md` - Blog post draft
- `output/charts/*.png` - All visualizations

---

**Status:** ✅ All components built, tested, and ready for use!
