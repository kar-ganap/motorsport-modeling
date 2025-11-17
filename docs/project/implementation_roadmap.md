# Implementation Roadmap with Go/No-Go Criteria

## Project Overview

**Goal:** Real-time race simulation system that predicts performance, detects technique issues, and recommends improvements.

**Demo Target:** Replay Indianapolis Race 1 lap-by-lap with:
- Live position predictions
- GPS racing line visualization
- Technique alerts and coaching recommendations
- Pit strategy optimization

---

## Phase 1: Data Foundation (Week 1)

### Objectives
Establish data infrastructure and validate we can extract meaningful insights from the telemetry.

### Tasks

#### 1.1 Data Loading Infrastructure
**Build:**
- Telemetry loader (handle long format → structured DataFrames)
- Lap timing loader
- Track metadata loader
- Data validation utilities

**Go/No-Go Criteria:**
- ✅ GO: Can load full Indianapolis dataset in <30 seconds
- ✅ GO: Can load sample data in <2 seconds
- ✅ GO: Data structures are memory-efficient (<2GB RAM for full race)
- ✅ GO: Missing data is identified and handled gracefully
- ❌ NO-GO: Data loading crashes or takes >5 minutes
- ❌ NO-GO: Can't handle telemetry format variations

**Validation Test:**
```python
# Load Race 1, Vehicle #55 (winner), Lap 7 (fastest lap)
df = load_telemetry('R1_indy.csv', vehicle=55, lap=7)
assert len(df) > 0
assert all(col in df.columns for col in ['speed', 'ath', 'pbrake_f'])
assert df['timestamp'].is_monotonic_increasing
```

#### 1.2 Basic Data Exploration
**Build:**
- Exploratory notebook analyzing sample data
- Data quality report (missing values, anomalies, gaps)
- Statistical summary of all 19 vehicles

**Go/No-Go Criteria:**
- ✅ GO: Can identify all 19 vehicles in Race 1
- ✅ GO: Can extract lap count per vehicle (should be ~26 laps)
- ✅ GO: GPS data is present and valid (lat/long within Indianapolis bounds)
- ✅ GO: All 12 telemetry parameters are present
- ❌ NO-GO: >20% of critical data is missing
- ❌ NO-GO: GPS data is corrupted or missing for winner

**Validation Test:**
```python
# Check data completeness
report = generate_data_quality_report('R1_indy.csv')
assert report['vehicles_found'] == 19
assert report['missing_gps_percent'] < 10
assert report['telemetry_parameters'] == 12
```

#### 1.3 Baseline Metrics Implementation
**Build:**
- Implement 3 high-confidence metrics:
  1. Lap time consistency (σ of lap times)
  2. Coasting time percentage
  3. Full throttle percentage

**Go/No-Go Criteria:**
- ✅ GO: Winner (#55) has lap time σ < 0.5s
- ✅ GO: Winner has lower coasting % than mid-pack drivers
- ✅ GO: Winner has higher full throttle % than mid-pack drivers
- ✅ GO: Metrics correlate with final race position (top 3 vs bottom 3)
- ❌ NO-GO: Metrics show no correlation with performance
- ❌ NO-GO: Winner's metrics are worse than P19

**Validation Test:**
```python
# Compare winner vs last place
winner_consistency = calculate_consistency(telemetry, vehicle=55)
last_place_consistency = calculate_consistency(telemetry, vehicle=X)
assert winner_consistency < last_place_consistency

winner_coasting = calculate_coasting_pct(telemetry, vehicle=55)
assert winner_coasting < 8.0  # Elite threshold
```

#### 1.4 GPS Visualization Proof-of-Concept
**Build:**
- Plot Indianapolis track layout from GPS
- Overlay racing line for winner (Vehicle #55)
- Color-code by speed

**Go/No-Go Criteria:**
- ✅ GO: Track shape is recognizable as Indianapolis road course
- ✅ GO: Racing line shows logical path through corners
- ✅ GO: Speed gradient shows braking zones (low) and straights (high)
- ❌ NO-GO: GPS coordinates don't form coherent track shape
- ❌ NO-GO: Can't distinguish corners from straights

**Validation Test:**
```python
# Visual inspection + automated bounds check
track_bounds = extract_track_bounds(gps_data)
assert 39.79 < track_bounds['lat_min'] < 39.80  # Indianapolis lat
assert -86.24 < track_bounds['lon_min'] < -86.23  # Indianapolis lon
```

### Phase 1 Gate Review

**Required to proceed to Phase 2:**
1. All data loaders working reliably
2. Data quality sufficient (>80% complete)
3. At least 2 of 3 baseline metrics show correlation with performance
4. GPS visualization is viable

**If NO-GO:**
- Reassess data quality issues
- Consider alternative tracks (Barber, COTA) if Indianapolis data is bad
- Pivot to non-GPS metrics if GPS is unusable

---

## Phase 2: Predictive Models (Week 2)

### Objectives
Build models that can predict future performance based on current data.

### Tasks

#### 2.1 Lap Time Degradation Model
**Build:**
- Train model on laps 1-15, predict laps 16-26
- Account for tire degradation
- Separate model for each driver or unified model

**Go/No-Go Criteria:**
- ✅ GO: RMSE < 0.5 seconds for lap time predictions
- ✅ GO: Can predict winner's final lap time within 1 second (from lap 15 data)
- ✅ GO: Model captures degradation trend (lap times increase over race)
- ❌ NO-GO: RMSE > 1.5 seconds
- ❌ NO-GO: Predictions show no degradation pattern

**Validation Test:**
```python
# Train on first 15 laps, test on last 11 laps
model = train_lap_time_model(telemetry, laps=range(1, 16))
predictions = model.predict(laps=range(16, 27))
actual = get_actual_lap_times(laps=range(16, 27))
rmse = calculate_rmse(predictions, actual)
assert rmse < 0.5
```

#### 2.2 Position Predictor
**Build:**
- Predict final race position from lap 20 data
- Model based on: pace delta, tire deg, gaps to cars ahead/behind

**Go/No-Go Criteria:**
- ✅ GO: Top 3 prediction accuracy >80% (from lap 20)
- ✅ GO: Winner correctly predicted from lap 15 data
- ✅ GO: Can identify which cars will gain/lose positions
- ❌ NO-GO: Random guessing (33% accuracy for podium)
- ❌ NO-GO: Can't predict winner until last lap

**Validation Test:**
```python
# Predict from lap 20, compare to actual finish
predictions = predict_positions(telemetry, current_lap=20)
actual_finish = get_actual_results()
top3_accuracy = calculate_top3_accuracy(predictions, actual_finish)
assert top3_accuracy > 0.8
```

#### 2.3 Technique Monitoring System
**Build:**
- Real-time monitoring of 5 key metrics:
  1. Braking smoothness
  2. Throttle application timing
  3. Coasting time
  4. Steering smoothness
  5. Corner minimum speed

**Go/No-Go Criteria:**
- ✅ GO: Can detect when driver's technique degrades (lap 10+ vs lap 3-5)
- ✅ GO: Runner-up (#2) shows measurable technique degradation vs winner
- ✅ GO: Degradation timing matches actual performance drop
- ❌ NO-GO: Winner shows same/worse technique than mid-pack
- ❌ NO-GO: Can't detect any technique changes during race

**Validation Test:**
```python
# Runner-up should show degradation that winner doesn't
winner_baseline = calculate_metrics(telemetry, vehicle=55, laps=[3,4,5])
winner_late = calculate_metrics(telemetry, vehicle=55, laps=[20,21,22])
assert winner_late['braking_smoothness'] > 0.8 * winner_baseline['braking_smoothness']

runner_up_baseline = calculate_metrics(telemetry, vehicle=2, laps=[3,4,5])
runner_up_late = calculate_metrics(telemetry, vehicle=2, laps=[20,21,22])
assert runner_up_late['braking_smoothness'] < 0.7 * runner_up_baseline['braking_smoothness']
```

#### 2.4 GPS Racing Line Comparison
**Build:**
- Extract racing lines for top 3 finishers
- Identify corners from GPS + speed data
- Compare lines at each corner (deviation, speed, time)

**Go/No-Go Criteria:**
- ✅ GO: Can identify 10+ distinct corners
- ✅ GO: Winner's line is faster than runner-up at ≥3 corners
- ✅ GO: Visual comparison shows meaningful differences
- ❌ NO-GO: Can't distinguish corners reliably
- ❌ NO-GO: All drivers have identical lines (no variation to analyze)

**Validation Test:**
```python
# Compare winner vs runner-up at key corner (Turn 5?)
winner_t5 = extract_corner_data(gps, vehicle=55, corner=5)
runner_t5 = extract_corner_data(gps, vehicle=2, corner=5)
time_delta = runner_t5['time'] - winner_t5['time']
assert time_delta > 0.05  # Runner-up slower by 50ms+
```

### Phase 2 Gate Review

**Required to proceed to Phase 3:**
1. Lap time predictions are viable (RMSE < 0.5s)
2. Can predict top 3 finish with >70% accuracy from lap 15
3. Technique monitoring detects real degradation
4. GPS analysis shows actionable differences

**If NO-GO:**
- Simplify models (less features, simpler algorithms)
- Focus on post-race analysis instead of real-time prediction
- Pivot to Category 3 (Post-Event Analysis) if predictions fail

---

## Phase 3: Real-Time Simulation & Dashboard (Week 3)

### Objectives
Build interactive demo that replays race with live predictions.

### Tasks

#### 3.1 Lap-by-Lap Replay Engine
**Build:**
- Process telemetry lap-by-lap (simulating real-time feed)
- Generate predictions at each lap
- Track prediction accuracy over time

**Go/No-Go Criteria:**
- ✅ GO: Can replay full race in <5 minutes
- ✅ GO: Predictions update smoothly lap-by-lap
- ✅ GO: No crashes during replay
- ❌ NO-GO: Replay takes >15 minutes
- ❌ NO-GO: Memory leaks or crashes

**Validation Test:**
```python
# Run full race replay
replay = RaceReplay('R1_indy.csv')
for lap in range(1, 27):
    replay.advance_to_lap(lap)
    predictions = replay.get_current_predictions()
    assert predictions is not None
```

#### 3.2 Interactive Dashboard
**Build:**
- Streamlit app with 4 panels:
  1. Live leaderboard (current + predicted)
  2. GPS track map with live positions
  3. Technique alerts (real-time warnings)
  4. Lap time graph (predicted vs actual)

**Go/No-Go Criteria:**
- ✅ GO: Dashboard loads in <10 seconds
- ✅ GO: All 4 panels render correctly
- ✅ GO: User can scrub through laps (slider/controls)
- ✅ GO: Visualizations are clear and readable
- ❌ NO-GO: Dashboard is unusably slow (>30s to load)
- ❌ NO-GO: Critical visualizations don't render

**Validation Test:**
```python
# Manual testing checklist
# - Load dashboard
# - Advance to lap 10
# - Verify GPS shows 19 cars in correct positions
# - Verify technique alert appears for runner-up
# - Verify predictions match stored values
```

#### 3.3 Demo Video
**Build:**
- 3-minute video showing:
  - Problem statement (0-30s)
  - Live replay demo (30-150s)
  - Key insights (150-180s)

**Go/No-Go Criteria:**
- ✅ GO: Video shows "wow factor" moments (accurate prediction, technique alert)
- ✅ GO: Explains value proposition clearly
- ✅ GO: Technical quality is professional (no glitches)
- ❌ NO-GO: Demo doesn't show any predictions
- ❌ NO-GO: Video quality is poor or confusing

### Phase 3 Gate Review

**Required for hackathon submission:**
1. Dashboard is functional and demonstrates key features
2. Demo video is complete and compelling
3. Code is on GitHub with README
4. Can show "before/after" (predicted vs actual) comparison

**If NO-GO:**
- Fall back to static dashboard (no real-time simulation)
- Use Jupyter notebook instead of Streamlit
- Focus on strongest 2-3 features instead of full system

---

## Minimum Viable Demo (Backup Plan)

If time runs short, the **absolute minimum** for submission:

### Must-Have
1. ✅ Working data loaders
2. ✅ 3 basic metrics calculated for all drivers
3. ✅ GPS visualization of winner's racing line
4. ✅ Static dashboard showing Race 1 analysis
5. ✅ README with clear documentation

### Nice-to-Have (drop if necessary)
- Real-time replay simulation
- Predictive models (focus on descriptive analysis)
- Interactive controls
- Technique alerts

### Submission Checklist
- [ ] Category selected (4 - Real-Time Analytics)
- [ ] Dataset documented (Indianapolis)
- [ ] Published project (Streamlit Cloud / GitHub Pages)
- [ ] Code repository (GitHub, public)
- [ ] Demo video (3 minutes)
- [ ] Text description (150 words)

---

## Risk Mitigation

### Risk 1: GPS Data Quality Issues
**Mitigation:** Have non-GPS metrics ready as backup (can still do time-series analysis)

### Risk 2: Predictions Don't Work
**Mitigation:** Pivot to post-race analysis (Category 3) - "Why did the winner win?"

### Risk 3: Dashboard Performance
**Mitigation:** Pre-compute all predictions, load from cache instead of real-time calculation

### Risk 4: Time Crunch
**Mitigation:** Focus on Phase 1 + 2, skip real-time simulation, use static Jupyter notebook

---

## Success Metrics (Final Evaluation)

### Technical Excellence
- Data loading is robust and efficient
- Metrics have clear methodology and validation
- Predictions are accurate (RMSE < 0.5s)
- Code is well-documented and tested

### Innovation
- Combines predictive + prescriptive analytics (not just dashboards)
- GPS racing line comparison is unique
- Real-time simulation angle is novel

### Practical Value
- Race engineers could actually use this
- Provides actionable coaching insights
- Could integrate into existing telemetry systems

### Presentation
- Demo is polished and impressive
- Video tells compelling story
- Documentation is clear and complete

---

## Current Status

**Completed:**
- [x] Project structure
- [x] Data sampling infrastructure
- [x] Sample data (5.8MB Indianapolis telemetry)

**Next Steps:**
1. Phase 1.1 - Data loading infrastructure
2. Phase 1.2 - Data exploration
3. Continue through roadmap...

---

## Decision Point: Where to Start?

Given the roadmap above, the critical path is:

**Phase 1.1 (Data Loaders)** → **Phase 1.2 (Exploration)** → **Phase 1.3 (Baseline Metrics)** → Gate Review

We can't do anything without being able to load and understand the data first.

**Recommendation:** Start with Phase 1.1 - Build robust data loaders and validate we can work with the telemetry format efficiently.

Does this roadmap make sense? Any phases you want to adjust or success criteria you want to change?
