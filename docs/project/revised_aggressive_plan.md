# Revised Implementation Plan - Aggressive but Achievable

**Target: Good Tier from Day 1, Ambitious Tier as achievable stretch**

---

## Week 1: Foundation + Predictive Core (Days 1-7)

### Day 1-2: Data Infrastructure + GPS Integration
**Morning Tasks:**
- [ ] Set up environment (uv, dependencies)
- [ ] Implement telemetry loader (long format → dataframe)
- [ ] Implement lap timing loader

**Afternoon Tasks:**
- [ ] **GPS corner identification** (don't wait for Week 3!)
  - Extract GPS coordinates
  - Cluster speed minima to identify ~10-12 corners
  - Create corner lookup table with GPS coords
- [ ] Data validation (19 vehicles, 12 parameters, GPS present)

**Success Criteria:**
- ✅ Load full Race 1 in <30s
- ✅ Identify 10+ distinct corners from GPS
- ✅ All 19 vehicles have complete data for winner's fastest lap

**If fails:** Data quality issue - need immediate debugging

---

### Day 3-4: Core Metrics with GPS Enhancement
**Tasks:**
- [ ] Implement 5 Tier 1 metrics:
  1. Consistency (lap time σ)
  2. Coasting time (%)
  3. Braking performance (peak pressure, pulses)
  4. Throttle timing (apex → full throttle)
  5. Steering smoothness (jerk)

- [ ] **Use GPS corners for precise metric calculation**
  - Per-corner braking analysis (not time-based guessing)
  - Per-corner minimum speed
  - Per-corner throttle application

**Validation:**
```python
# Winner must score better on at least 4 of 5 metrics
winner = calculate_metrics(vehicle=55)
last_place = calculate_metrics(vehicle=19)
assert sum(winner[m] > last_place[m] for m in metrics) >= 4
```

**Success Criteria:**
- ✅ All 5 metrics calculate successfully
- ✅ Winner scores better than P19 on ≥4 metrics
- ✅ Metrics show correlation with finishing position (Spearman ρ > 0.3)

**If fails:** Metric definitions need adjustment

---

### Day 5-6: Basic Predictive Model
**Tasks:**
- [ ] Lap time degradation model
  ```python
  # Simple linear model first
  lap_times = [128.5, 129.1, 129.8, 130.2, ...]
  degradation_rate = fit_linear(lap_times, lap_numbers)

  # Predict future laps
  predicted_lap_25 = lap_1_time + (degradation_rate * 24)
  ```

- [ ] **Train on Race 1, validate on Race 2**
  - Race 1: Training data
  - Race 2: Test data (never seen during training)

**Success Criteria:**
- ✅ Race 1 RMSE < 1.0s (in-sample)
- ✅ Race 2 RMSE < 1.5s (out-of-sample)
- ✅ Can predict winner from lap 15 data

**Tiered Success:**
- Excellent: Race 2 RMSE < 0.8s
- Good: Race 2 RMSE < 1.2s
- Acceptable: Race 2 RMSE < 1.5s
- Rework needed: Race 2 RMSE > 1.5s

---

### Day 7: Minimal Dashboard
**Tasks:**
- [ ] Simple Streamlit app with 3 views:
  1. Driver leaderboard (sorted by composite metric score)
  2. Lap time graph with predictions overlaid
  3. Winner vs runner-up comparison

**Success Criteria:**
- ✅ Dashboard loads in <10s
- ✅ Shows predictions vs actual
- ✅ Can demo to someone and they understand it

**END OF WEEK 1 GATE:**
- ✅ **GREEN:** Have predictions working, Race 2 RMSE < 1.2s → Proceed to Week 2
- ⚠️ **YELLOW:** Predictions work but RMSE 1.2-1.5s → Consolidate Week 2
- ❌ **RED:** Predictions don't work → Reassess approach

**Deliverable:** Working Good Tier prototype (minimal but functional)

---

## Week 2: Advanced Predictions + GPS Visualization (Days 8-14)

### Day 8-9: Remaining Metrics + Technique Monitoring
**Tasks:**
- [ ] Implement Tier 2 metrics:
  6. G-force utilization
  7. Minimum corner speed (GPS-enhanced)
  8. Brake-turn overlap

- [ ] Implement Tier 3 metrics:
  9. Throttle-steering coordination
  10. Tire degradation pattern

- [ ] Technique degradation detector:
  ```python
  # Compare lap 3-5 baseline vs laps 20-22
  baseline = calculate_metrics(laps=[3,4,5])
  late_race = calculate_metrics(laps=[20,21,22])

  if late_race['braking'] < 0.7 * baseline['braking']:
      alert = "Braking degrading - smooth brake release"
  ```

**Success Criteria:**
- ✅ All 10 metrics implemented
- ✅ Can detect runner-up's technique degradation
- ✅ Winner shows less degradation than runner-up

---

### Day 10-11: Position Prediction + Cross-Race Analysis
**Tasks:**
- [ ] Position prediction model:
  ```python
  # Based on pace delta to cars ahead/behind
  def predict_final_position(driver, current_lap):
      pace_delta = my_pace - their_pace
      laps_to_catch = gap / abs(pace_delta)
      if laps_to_catch < remaining_laps:
          return current_position ± 1
  ```

- [ ] **Cross-race analysis:**
  - Did drivers improve between Race 1 and Race 2?
  - Which metrics showed most improvement?
  - Did our recommendations (if followed) correlate with improvement?

**Success Criteria:**
- ✅ Top-3 prediction accuracy >70% from lap 20
- ✅ Can identify which drivers improved Race 1→Race 2

---

### Day 12-14: GPS Racing Line Visualization
**Tasks:**
- [ ] Extract racing lines from GPS
  ```python
  winner_line = get_gps_trace(vehicle=55, lap=7)  # Fastest lap
  runner_up_line = get_gps_trace(vehicle=2, lap=7)

  plt.plot(winner_line.lon, winner_line.lat,
           color='green', linewidth=3, label='Winner')
  plt.plot(runner_up_line.lon, runner_up_line.lat,
           color='red', linewidth=2, alpha=0.7, label='P2')
  ```

- [ ] Speed heatmap overlay:
  ```python
  plt.scatter(gps.lon, gps.lat, c=gps.speed,
              cmap='RdYlGn', s=10)
  plt.colorbar(label='Speed (km/h)')
  ```

- [ ] **Per-corner comparison:**
  - At each of 10 corners, show both lines
  - Color-code by speed
  - Show time delta at each corner

**Success Criteria:**
- ✅ Track shape recognizable as Indianapolis
- ✅ Winner's line visibly different from runner-up at ≥3 corners
- ✅ Can show where winner gains time (corner-by-corner)

**END OF WEEK 2 GATE:**
- ✅ **GREEN:** GPS viz working, predictions validated → Proceed to Stretch Goal
- ⚠️ **YELLOW:** Most features work, some polish needed → Week 3 polish
- ❌ **RED:** Major features missing → Focus Week 3 on completion

**Deliverable:** Complete Good Tier + GPS visualization

---

## Week 3: Stretch Goal OR Polish (Days 15-21)

### DECISION POINT: Choose ONE path

---

## 🎯 STRETCH GOAL OPTION A: "Counterfactual Analysis Engine"

**The Big Idea:**
> "Runner-up lost by 0.17s. Show EXACTLY how they could have won."

### Day 15-17: Counterfactual Simulator

**Build:**
```python
def simulate_corrected_performance(driver, corrections):
    """
    Simulate race with technique corrections applied.

    Example:
    corrections = {
        'from_lap': 12,
        'to_lap': 26,
        'improvements': {
            'braking_smoothness': +20%,  # Reduce pulse count
            'coasting_time': -30%,       # Less coasting
        }
    }

    Returns: Adjusted lap times, final gap to winner
    """
    original_laps = get_lap_times(driver)
    adjusted_laps = original_laps.copy()

    for lap in range(corrections['from_lap'], corrections['to_lap']):
        # Calculate time gain from each improvement
        time_gain = 0
        if 'braking_smoothness' in corrections:
            time_gain += 0.15  # 150ms per lap from smoother braking
        if 'coasting_time' in corrections:
            time_gain += 0.12  # 120ms per lap from less coasting

        adjusted_laps[lap] = original_laps[lap] - time_gain

    return adjusted_laps
```

**The Demo Moment:**
```
"Let's analyze runner-up #2 Robusto..."

[Show actual race]
Final gap to winner: +0.170s (P2)

[Show technique degradation]
Lap 12-26: Braking smoothness dropped 35%
            Coasting time increased 40%

[Run counterfactual]
"If driver #2 had maintained lap 1-10 braking quality..."

Adjusted lap times:
- Lap 12: 1:40.8 → 1:40.5 (-0.3s)
- Lap 15: 1:41.2 → 1:40.8 (-0.4s)
- Lap 20: 1:41.8 → 1:41.3 (-0.5s)

Cumulative time saved: 4.2 seconds over 15 laps

[Show result]
Adjusted final gap: -0.05s (RACE WIN!)

CONCLUSION: Driver #2 had winning pace until lap 12.
Technique degradation cost them the race.
Maintaining baseline quality would have resulted in victory.
```

**Success Criteria:**
- ✅ Counterfactual shows plausible alternative outcome
- ✅ Time gains are defensible (based on metric deltas)
- ✅ Visual comparison: actual vs counterfactual lap times

**Wow Factor:** ⭐⭐⭐⭐⭐ (This is the narrative judges want)

---

## 🎯 STRETCH GOAL OPTION B: "Animated Race Replay"

**The Big Idea:**
> "Watch the race unfold with live predictions and alerts"

### Day 15-17: Animation Engine

**Build:**
```python
import matplotlib.animation as animation

def animate_race(race_data):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))

    # Left: GPS track with car positions
    ax1.plot(track.lon, track.lat, 'k-', linewidth=2)
    cars = [ax1.scatter([], [], s=100, label=f'Car {i}')
            for i in range(19)]

    # Right: Live predictions graph
    ax2.plot([], [], label='Predicted')
    ax2.plot([], [], label='Actual')

    def update(lap_number):
        # Update car positions on track
        for i, car in enumerate(cars):
            pos = get_position(vehicle=i, lap=lap_number)
            car.set_offsets([pos.lon, pos.lat])

        # Update predictions
        predictions = predict_from_lap(lap_number)
        # ... update graph ...

        # Show alerts
        if lap_number == 12:
            ax1.text(0.5, 0.95, '⚠️ Car #2: Braking degrading',
                    transform=ax1.transAxes, fontsize=14)

    anim = animation.FuncAnimation(fig, update, frames=range(1, 27),
                                   interval=500, repeat=False)
    return anim
```

**Success Criteria:**
- ✅ Can replay full race (26 laps) in ~2 minutes
- ✅ Car positions update smoothly on GPS track
- ✅ Predictions update lap-by-lap
- ✅ Technique alerts appear at correct laps

**Wow Factor:** ⭐⭐⭐⭐ (Very visual, impressive demo)

---

## 🎯 STRETCH GOAL OPTION C: "Pit Strategy Optimizer"

**The Big Idea:**
> "Calculate optimal pit window accounting for tire degradation"

### Day 15-17: Strategy Module

**Build:**
```python
def optimal_pit_window(driver, current_lap, race_length=26):
    """
    Calculate when tire degradation cost exceeds pit stop time loss.
    """
    pit_time_loss = 25  # seconds (pit lane + lost positions)
    degradation_rate = calculate_degradation_rate(driver)

    for pit_lap in range(current_lap, race_length - 5):
        remaining_laps = race_length - pit_lap

        # Time lost on old tires
        old_tire_time_loss = sum(
            degradation_rate * (lap - pit_lap)
            for lap in range(pit_lap, race_length)
        )

        # Compare to pit stop cost
        if old_tire_time_loss > pit_time_loss:
            return {
                'optimal_pit_lap': pit_lap,
                'time_saved': old_tire_time_loss - pit_time_loss,
                'projected_position': simulate_pit_strategy(driver, pit_lap)
            }

    return None  # No pit beneficial
```

**Success Criteria:**
- ✅ Can calculate pit window for each driver
- ✅ Recommendation accounts for tire deg + position changes
- ✅ Can show "pit now vs pit later" comparison

**Wow Factor:** ⭐⭐⭐ (Practical but less visually impressive)

---

## My Recommendation: STRETCH GOAL OPTION A

**Why Counterfactual Analysis:**

1. **Tells the best story:**
   - "Driver X could have won by doing Y"
   - Directly actionable for teams
   - Creates emotional connection

2. **Technically achievable:**
   - Uses metrics we already have
   - Physics-based time calculations
   - No complex animation needed

3. **Highly defensible:**
   - Based on measured technique differences
   - Time gains are quantifiable
   - Can validate with "what actually happened"

4. **Perfect for demo video:**
   ```
   Minute 1: "0.17s separated winner from runner-up"
   Minute 2: "We found why #2 lost - technique degraded lap 12+"
   Minute 3: "If they'd maintained quality, they would've won by 0.05s"
   ```

5. **Aligns with hackathon goal:**
   - Real-time analytics ✓
   - Race engineer decision-making ✓
   - Actionable recommendations ✓

---

## Fallback Plans

**If Week 2 is YELLOW (not GREEN):**
→ Skip stretch goal entirely
→ Use Week 3 for polish and documentation
→ Submit polished Good Tier

**If Week 1 is YELLOW:**
→ Compress Week 2 timeline
→ Skip stretch goal
→ Submit Good Tier at end of Week 2

**If Week 1 is RED:**
→ Immediate reassessment
→ Consider data quality issues
→ May need to pivot approach

---

## Summary: Aggressive Timeline

| Week | Target | Deliverable |
|------|--------|-------------|
| **Week 1** | Foundation + Predictions | Working prototype with lap time predictions (Good Tier minimal) |
| **Week 2** | Full Metrics + GPS | Complete Good Tier + GPS visualization |
| **Week 3** | Counterfactual Analysis | Ambitious Tier with "could have won" story |

**Key Differences from Original Plan:**

1. ✅ **GPS from Day 1** (not Week 3)
2. ✅ **Predictions in Week 1** (not Week 2)
3. ✅ **Race 2 validation throughout** (not afterthought)
4. ✅ **True stretch goal** (counterfactual, not just polish)
5. ✅ **Category 4 compliant from Day 1** (not building Baseline first)

---

## What do you think?

1. Is this timeline more appropriate?
2. Does Counterfactual Analysis seem like the right stretch goal?
3. Ready to start Day 1 with this plan?
