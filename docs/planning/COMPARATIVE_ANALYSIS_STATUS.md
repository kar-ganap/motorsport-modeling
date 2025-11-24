# Comparative Analysis Implementation Status

## What We've Built

### 1. Comprehensive Plan (COUNTERFACTUAL_IMPLEMENTATION_PLAN.md)
- ✅ Detailed architecture for comparative vs counterfactual analysis
- ✅ Data requirements mapped
- ✅ Implementation roadmap with phases
- ✅ Cost analysis showing LLM narratives are ~$1-5/month

### 2. Core Comparative Module (src/motorsport_modeling/analysis/comparative.py)
- ✅ `FieldBenchmark` class - computes field-wide statistics (median, P25/P75, top5)
- ✅ `DriverMetrics` dataclass - structured metrics for LLM consumption
- ✅ `compute_driver_deltas()` - pace comparison vs field
- ✅ `segment_race()` - early/mid/late stint segmentation
- ✅ `detect_traffic_laps()` - identifies laps in traffic
- ✅ `compute_degradation_rate()` - calculates pace degradation
- ✅ `compute_driver_metrics()` - comprehensive metric computation

## What's Next

### Immediate Tasks (in order):

**1. Create GPT-4o Narrative Generator** (30 min)
- File: `src/motorsport_modeling/analysis/narrative_generator.py`
- Function: `generate_comparative_narrative(metrics: DriverMetrics) -> str`
- Uses OpenAI GPT-4o API
- Input: Structured DriverMetrics
- Output: Professional 2-3 sentence analysis

**2. Update Precompute Script** (30 min)
- File: `scripts/precompute_race_analytics.py`
- Add comparative analysis computation
- Generate narratives for each driver
- Save to `{track}/{race}_comparative.parquet`

**3. Update Dashboard** (30 min)
- File: `pages/1_Race_Analytics.py`
- Replace current counterfactual section (lines 1165-1400)
- Load precomputed comparative analysis
- Display metrics + LLM narrative

**4. Test on Sample Race** (15 min)
- Run on vir/race1
- Validate narratives make sense
- Check cost (~$0.10 for 25 drivers)

## Key Design Decisions

### 1. Hybrid Approach
- **Compute metrics**: Deterministic, fast, always available
- **Generate narrative**: GPT-4o adds context and professionalism
- **Dashboard displays both**: Charts + Text

### 2. Pre-computation Strategy
- Generate all narratives during `precompute_race_analytics.py`
- Store in parquet alongside metrics
- Dashboard loads instantly (no API calls at runtime)
- Total cost: ~$0.10 per race = $1.40 for full season

### 3. GPT-4o Choice
- Faster than Claude
- Cheaper ($0.15/1M input, $0.60/1M output vs Claude's $3/$15)
- Still high quality for structured narrative generation
- Estimated cost per narrative: $0.004 (less than half a penny)

## File Structure

```
src/motorsport_modeling/
├── analysis/
│   ├── comparative.py          # ✅ DONE - Field benchmarks, metrics
│   └── narrative_generator.py  # 🔨 NEXT - GPT-4o integration
│
scripts/
└── precompute_race_analytics.py  # 🔨 UPDATE - Add comparative analysis

pages/
└── 1_Race_Analytics.py           # 🔨 UPDATE - Replace counterfactual

data/processed/{track}/{race}/
└── comparative.parquet            # 🔨 NEW - Precomputed narratives
```

## Sample Output

### Metrics (Always Available)
```python
{
    "vehicle_number": 13,
    "final_position": 2,
    "gap_to_winner": 3.5,
    "early_delta": -0.2,     # 0.2s faster than field
    "mid_delta": 0.1,         # 0.1s slower
    "late_delta": 0.5,        # 0.5s slower
    "driver_deg": 0.78,       # 0.78s/lap degradation
    "field_deg": 0.45,        # field average
    "deg_delta": 0.33,        # 0.33s/lap worse
    "traffic_laps": 8,
    "traffic_cost": 2.1,      # 2.1s lost to traffic
}
```

### Narrative (GPT-4o Generated)
```
"Tire degradation was the primary performance limiter, with a 0.78s/lap
degradation rate significantly exceeding the field average of 0.45s/lap.
This cost approximately 5 seconds over the stint relative to the leaders.
The early-race pace advantage of 0.2s/lap suggests strong tire management
technique or setup optimization could yield 3-4 seconds without sacrificing
qualifying speed. Traffic on laps 8-12 cost an additional 2.1s, but the
degradation gap represents the larger opportunity."
```

## Next Session Plan

1. Create `narrative_generator.py` with GPT-4o integration
2. Add comparative analysis to precompute script
3. Test on one race (vir/race1)
4. If working, run on all races
5. Update dashboard to use precomputed data
6. Validate narratives make sense for different drivers/positions

## Environment Setup Needed

Add to `.env`:
```bash
OPENAI_API_KEY=your_key_here
```

## Cost Tracking

Keep running tally:
- Test race (25 drivers): ~$0.10
- Full season (14 races × 25 drivers): ~$1.40
- Development/testing iterations: ~$0.50
- **Total expected cost: <$2.00**
