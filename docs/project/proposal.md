# Project Proposal: "RaceCraft AI - Real-Time Performance Predictor & Coach"

## Primary Category: **Category 4 - Real-Time Analytics**

**With strong Category 1 (Driver Training) elements embedded**

---

## Executive Summary

Build a **real-time race simulation and coaching system** that:
1. **Predicts** lap-by-lap performance degradation and position changes
2. **Detects** when a driver is underperforming vs. their potential
3. **Recommends** specific technique improvements in real-time
4. **Simulates** "what-if" scenarios (pit now vs. pit in 2 laps)

**Demo "Wow Factor":** Replay Indianapolis Race 1 lap-by-lap with live predictions, GPS racing lines, and real-time coaching alerts.

---

## Why Category 4 (Real-Time Analytics) as Primary?

### From the Rules:
> "Design a tool that simulates real-time decision-making for a race engineer. What's the perfect pit stop window? How can you react to a caution flag?"

### Our Angle:
**"Real-time" doesn't mean live hardware - it means simulating the race engineer's decision process during the race.**

We'll build a system that:
- Processes telemetry lap-by-lap (simulating real-time feed)
- Makes predictions about future performance
- Provides actionable recommendations
- Shows "what would have happened" with different decisions

**Category 1 elements** (driver training) become the **recommendation engine** within the Category 4 tool.

---

## The Core Concept: "Digital Race Engineer"

### Real Race Engineer's Job:
During a race, the engineer monitors:
1. Driver's current lap times vs. expected
2. Tire degradation rate
3. Gap to cars ahead/behind
4. Optimal pit window
5. Driver technique quality (smooth/aggressive/mistakes)

**Our tool does all of this, but with AI-powered predictions.**

### The Innovation:
**Combine predictive modeling (where will the driver be in 5 laps?) with prescriptive analytics (how can they improve?)**

```
Traditional Race Engineer:
"You're 2 seconds behind P4. Push harder!"

RaceCraft AI:
"You're 2 seconds behind P4. Your braking is 0.3s slower per lap.
Brake 10m later at Turn 5 → gain 0.5s → catch P4 in 4 laps.
Alternative: Current pace reaches P4 in 7 laps if their tires degrade."
```

---

## System Architecture

### Input Data (Indianapolis - All Sources)

**1. Telemetry (21.4M rows)**
- Speed, throttle, brakes, steering, G-forces
- GPS coordinates (4.47M points)
- Lap distance tracking

**2. Lap Timing**
- Sector times (S1, S2, S3)
- Lap start/end timestamps
- Intermediate splits

**3. Race Results**
- Final positions
- Gap analysis
- Fastest laps

**4. Track Geometry (from vir.json pattern)**
- Sector lengths
- Track layout

**5. Weather Data (if available for Indy)**
- Temperature, humidity, wind

### Processing Pipeline

```
┌─────────────────────────────────────────────────────────┐
│  OFFLINE: Model Training (Race 1 data)                 │
├─────────────────────────────────────────────────────────┤
│  1. Technique Quality Models (10 metrics per driver)   │
│  2. Tire Degradation Model (lap time vs. lap number)   │
│  3. Sector Performance Model (S1/S2/S3 patterns)        │
│  4. Driver Comparison Model (winner vs. field)         │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│  REAL-TIME SIMULATION: Replay Race Lap-by-Lap          │
├─────────────────────────────────────────────────────────┤
│  Lap 1:  Baseline performance established              │
│  Lap 5:  Predict lap time for lap 10 (degradation)     │
│  Lap 7:  Detect: Driver #2 braking too early           │
│          → Coaching: "Brake 8m later at T5"            │
│  Lap 10: Predict: When will tire delta favor pit stop? │
│  Lap 15: Predict: Position after pit stop              │
│  Lap 20: Predict: Final position based on current pace │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│  OUTPUT: Real-Time Dashboard                            │
├─────────────────────────────────────────────────────────┤
│  • Live position tracker (GPS visualization)            │
│  • Lap time predictions (next lap, final position)     │
│  • Technique alerts ("Braking quality degrading!")     │
│  • Strategy recommendations ("Pit window: Lap 12-14")  │
│  • What-if simulator ("Pit now: P5 → P7 for 2 laps")  │
└─────────────────────────────────────────────────────────┘
```

---

## Core Features (MVP)

### Feature 1: Predictive Lap Time Model
**Category 4 - Core**

```python
# Train on laps 1-15 from Race 1
def predict_lap_time(driver, current_lap):
    # Factors:
    # - Baseline pace (avg of laps 3-5)
    # - Tire degradation rate (learned from data)
    # - Track evolution (race gets faster)
    # - Driver consistency (σ of lap times)

    baseline = driver.avg_lap_time[3:5]
    tire_deg = driver.degradation_rate * (current_lap - 5)
    track_improvement = -0.05 * current_lap  # Track rubbers in

    predicted = baseline + tire_deg + track_improvement
    return predicted ± driver.consistency_std

# Example output:
# Lap 10 prediction: 1:40.8 ± 0.3s
# Actual: 1:40.5s → Driver performing above expectation!
```

### Feature 2: Real-Time Technique Monitoring
**Category 1 element within Category 4**

```python
# Monitor 10 high-confidence metrics in real-time
def monitor_driver_technique(driver, current_lap):
    current_metrics = calculate_metrics(driver.telemetry[current_lap])
    baseline_metrics = driver.metrics_baseline  # From laps 1-5

    alerts = []

    if current_metrics['braking_smoothness'] < baseline_metrics['braking_smoothness'] * 0.8:
        alerts.append({
            'severity': 'warning',
            'category': 'braking',
            'message': 'Braking quality degraded: +3 brake pulses per corner',
            'recommendation': 'Smooth brake release. Focus on Turn 5.',
            'time_gain': '0.4s per lap'
        })

    if current_metrics['coasting_time'] > baseline_metrics['coasting_time'] * 1.3:
        alerts.append({
            'severity': 'critical',
            'category': 'efficiency',
            'message': 'Coasting increased from 4% to 7% of lap',
            'recommendation': 'Commit to throttle earlier at Turn 8 exit',
            'time_gain': '0.3s per lap'
        })

    return alerts
```

### Feature 3: Pit Strategy Optimizer
**Category 4 - Core**

```python
def optimal_pit_window(driver, current_lap, race_laps=26):
    # Calculate when tire degradation > pit time loss

    pit_time_loss = 25  # seconds (includes pit lane time + lost positions)

    tire_delta_per_lap = driver.degradation_rate  # e.g., 0.12s/lap

    # On lap N with old tires vs. fresh tires:
    # If we pit, we lose 25s but gain (tire_delta * remaining_laps)

    for pit_lap in range(current_lap, race_laps - 5):
        remaining_laps = race_laps - pit_lap

        # Time lost by NOT pitting:
        tire_time_loss = tire_delta_per_lap * (remaining_laps ** 2) / 2

        if tire_time_loss > pit_time_loss:
            return {
                'optimal_pit_lap': pit_lap,
                'reason': f'Tire delta ({tire_time_loss:.1f}s) exceeds pit loss ({pit_time_loss}s)',
                'projected_position': calculate_position_after_pit(driver, pit_lap)
            }

    return {'optimal_pit_lap': None, 'reason': 'No pit needed - manage tires'}
```

### Feature 4: Position Predictor
**Category 4 - Core**

```python
def predict_final_position(driver, current_lap, current_position):
    # Based on:
    # 1. Current pace vs. cars ahead/behind
    # 2. Tire degradation rates (relative)
    # 3. Historical overtaking locations (GPS analysis)

    gaps_ahead = get_gaps_to_cars_ahead(driver, current_lap)
    gaps_behind = get_gaps_to_cars_behind(driver, current_lap)

    pace_delta_ahead = driver.predicted_pace - gaps_ahead['driver'].predicted_pace
    pace_delta_behind = driver.predicted_pace - gaps_behind['driver'].predicted_pace

    laps_remaining = 26 - current_lap

    # Will we catch car ahead?
    if pace_delta_ahead < 0:  # We're faster
        laps_to_catch = gaps_ahead['gap'] / abs(pace_delta_ahead)
        if laps_to_catch < laps_remaining:
            predicted_position = current_position - 1

    # Will car behind catch us?
    if pace_delta_behind > 0:  # They're faster
        laps_to_catch = gaps_behind['gap'] / abs(pace_delta_behind)
        if laps_to_catch < laps_remaining:
            predicted_position = current_position + 1

    return {
        'predicted_final_position': predicted_position,
        'confidence': calculate_confidence(laps_remaining),
        'factors': [pace_delta_ahead, pace_delta_behind, tire_states]
    }
```

### Feature 5: GPS Racing Line Comparator
**Demo Wow Factor - Visual**

```python
def compare_racing_lines(driver_a, driver_b, lap_number):
    # Extract GPS for both drivers on same lap
    gps_a = get_gps_data(driver_a, lap_number)
    gps_b = get_gps_data(driver_b, lap_number)

    # Identify corners from GPS (speed minima + GPS clustering)
    corners = identify_corners_from_gps(gps_a)

    # For each corner, show difference
    for corner in corners:
        line_a = gps_a[corner.start:corner.end]
        line_b = gps_b[corner.start:corner.end]

        # Calculate deviation
        deviation = calculate_line_deviation(line_a, line_b)

        # Which line was faster?
        time_a = line_a.timestamp[-1] - line_a.timestamp[0]
        time_b = line_b.timestamp[-1] - line_b.timestamp[0]

        winner = 'A' if time_a < time_b else 'B'
        delta = abs(time_a - time_b)

        visualize_corner_comparison(line_a, line_b, winner, delta)
```

---

## Data Usage Map (Indianapolis - All Sources)

| Data Source | Feature Using It | Purpose |
|-------------|------------------|---------|
| **Telemetry (speed, throttle, brake)** | Technique Monitoring | Calculate 10 metrics, detect degradation |
| **Telemetry (GPS)** | Racing Line Comparison | Visual overlay, corner analysis |
| **Telemetry (lap distance)** | Corner Identification | Know which corner is which without time heuristics |
| **Lap times (total)** | Predictive Model | Train degradation curve, predict future laps |
| **Sector times (S1/S2/S3)** | Performance Breakdown | Identify which sector driver is weak |
| **Lap start/end** | Position Tracking | Calculate gaps, predict overtakes |
| **Race results** | Ground Truth | Validate predictions, show "what actually happened" |
| **Track geometry** | Strategy Calculations | Pit lane time, sector distances |
| **Weather** (if available) | Contextualize Performance | "Hot track = more degradation" |

**Result:** Using 100% of available Indianapolis data sources!

---

## Demo Flow (The "Wow Factor")

### Live Dashboard Replay: Indianapolis Race 1

**Setup:**
```
Screen shows:
┌─────────────────────────────────────────────────────────┐
│ [Track Map with GPS]  │ [Live Leaderboard]             │
│                       │  1. #55 Kohlbecker  Gap: ---   │
│  [Racing lines of     │  2. #2  Robusto     +0.2s      │
│   top 3 cars]         │  3. #13 Workman     +0.5s      │
│                       │  ...                            │
├───────────────────────┴─────────────────────────────────┤
│ [Lap Time Graph]      │ [Technique Alerts]             │
│ Predicted vs Actual   │ ⚠️  #2: Braking degrading      │
│                       │ 💡 Recommendation: Smooth T5   │
│                       │ 📈 Est. gain: +0.4s/lap        │
└─────────────────────────────────────────────────────────┘
```

**Playback (Lap-by-Lap):**

**Lap 1-3:** System learns baseline
- "Establishing driver baselines..."
- Show 10 metrics for top 3 drivers
- Predict: "Winner will be #55, #2, or #13 (too close to call)"

**Lap 5:** First predictions
- "Predicting lap 10 times based on current degradation..."
- Show predicted lap times: #55: 1:40.5±0.2, #2: 1:40.8±0.3
- GPS overlay: Show all 3 drivers' lines at Turn 5 (colored by speed)

**Lap 7:** Winner's fastest lap
- "🏁 #55 sets fastest lap: 1:39.748 (predicted 1:39.9)"
- Highlight: "Superior braking at T5: 122 bar peak, 0 pulses"
- Show GPS: Winner's line vs. #2's line at T5 (visual difference)

**Lap 12:** Technique alert for #2
- "⚠️ Alert: #2 Robusto braking quality degrading"
- Show: Brake pulse count increased from 0.8 to 2.3 per corner
- Recommendation: "Focus on Turn 5 brake release smoothness"
- Prediction: "If not corrected, will lose additional 0.3s/lap"

**Lap 15:** Pit strategy window
- "Optimal pit window for #2: Lap 18-20"
- Calculation shown: "Current tire delta = 1.2s, pit loss = 25s"
- What-if: "Pit now → P5, Pit lap 18 → P3"

**Lap 20:** Position prediction
- "5 laps remaining. Predicting final positions..."
- #55: P1 (99% confidence)
- #2: P2 (85% confidence - gap to #55 stabilizing at 0.2s)
- #13: P3 (75% confidence - #2 pulling away)

**Lap 26 (Finish):**
- "ACTUAL: #55 wins by 0.170s (predicted 0.2s ✓)"
- "Post-race analysis: #2 lost 0.4s in laps 10-15 due to braking degradation"
- "If #2 had corrected braking: Estimated final gap: 0.05s (race win possible!)"

**Final Screen:**
```
Race Analysis Summary:
┌─────────────────────────────────────────────────┐
│ Winner: #55 Kohlbecker (predicted correctly)   │
│ Winning margin: 0.170s (predicted 0.2s - 15% error) │
│                                                 │
│ Key Insight:                                    │
│ #2 Robusto had winning pace until lap 10       │
│ Braking degradation cost 0.4s total            │
│ → Correctable with real-time coaching          │
│                                                 │
│ Recommendations for #2 (next race):            │
│ ✓ Maintain braking smoothness (0 pulses)       │
│ ✓ Focus on Turn 5 exit throttle application    │
│ ✓ Estimated improvement: 0.5s/lap → P1         │
└─────────────────────────────────────────────────┘
```

---

## Technical Implementation Plan

### Week 1: Data Engineering + Baseline
- [ ] Extract Indianapolis data
- [ ] Build telemetry loader (handle 21M rows efficiently)
- [ ] Calculate 10 high-confidence metrics for all 19 drivers
- [ ] Train tire degradation model (lap time vs. lap number)
- [ ] Validate: Predict Race 1 final positions from lap 20 data

**Deliverable:** Python module that scores all drivers + prediction accuracy metrics

### Week 2: Predictive Models + GPS
- [ ] Build lap time predictor (RMSE < 0.5s)
- [ ] Build position predictor (accuracy > 80%)
- [ ] Extract and clean GPS data
- [ ] Plot racing lines for top 5 drivers
- [ ] Identify corners from GPS + speed

**Deliverable:** Prediction models + GPS visualization notebook

### Week 3: Real-Time Simulation + Dashboard
- [ ] Build lap-by-lap replay engine
- [ ] Integrate predictions into timeline
- [ ] Create technique alerts system
- [ ] Build interactive dashboard (Streamlit/Dash)
- [ ] Record demo video

**Deliverable:** Working demo + video

---

## Competitive Advantages

### 1. **True Real-Time Decision Making**
Not just "show the data" - actually **predict and recommend** like a race engineer

### 2. **Combines Predictive + Prescriptive**
- **Predictive:** "You'll finish P3"
- **Prescriptive:** "Brake smoother to finish P2"

### 3. **Uses Full Dataset**
Every data source in Indianapolis is utilized (not just telemetry)

### 4. **Validates Predictions**
We can show "predicted vs. actual" using historical race (builds trust)

### 5. **Actionable for Teams**
Real teams can use this system to:
- Analyze races post-event
- Train drivers with specific feedback
- Test strategies before race day

---

## Addressing Hackathon Criteria

### **Category:** Real-Time Analytics ✓

**From rules:** "Design a tool that simulates real-time decision-making for a race engineer."

**Our answer:** Lap-by-lap replay with predictions, alerts, and recommendations.

### **Innovation:**

Not just showing data - **predicting future performance and prescribing improvements**

### **Technical Depth:**

- Machine learning (degradation models, position prediction)
- Signal processing (technique metrics from telemetry)
- GPS analysis (racing line extraction)
- Real-time simulation (lap-by-lap processing)

### **Practical Value:**

GR Cup teams can actually use this to:
1. Review races to find improvement areas
2. Train drivers with data-backed coaching
3. Test "what-if" strategies

### **Presentation:**

Visual GPS overlays + live predictions = high wow factor

---

## Backup Plan (If Week 3 Time Runs Short)

**Minimum Viable Demo:**
1. Static dashboard showing Race 1 analysis
2. Predictions for 5 key laps (5, 10, 15, 20, finish)
3. Technique analysis for top 3 drivers
4. GPS racing line comparison (winner vs. runner-up)

**Still Category 4 compliant:** Shows "what a race engineer would see" even if not fully real-time

---

## Final Submission Package

**1. Category:** Real-Time Analytics (with Driver Training elements)

**2. Dataset:** Indianapolis Motor Speedway (both races)

**3. Text Description:**
"RaceCraft AI is a real-time race engineering assistant that predicts lap-by-lap performance, detects technique degradation, and recommends specific improvements. By combining predictive modeling with GPS-enhanced coaching insights, it enables teams to make data-driven decisions during races and optimize driver training between events."

**4. Published Project:**
- Interactive dashboard (Streamlit Cloud or Heroku)
- URL: `https://racecraft-ai.streamlit.app`

**5. Code Repository:**
- GitHub: Well-documented Python package
- Includes: data loaders, metric calculators, predictive models, visualization tools

**6. Demo Video (3 minutes):**
- 0:00-0:30: Problem statement
- 0:30-1:30: Live replay demo (condensed race)
- 1:30-2:30: Key features (predictions, alerts, GPS)
- 2:30-3:00: Impact and future work

---

## Why This Will Win

✅ **Clearly fits Category 4** (real-time analytics)
✅ **Has predictive elements** (your desired focus)
✅ **Has "wow factor"** (GPS visualization + live predictions)
✅ **Uses full Indianapolis dataset** (all data sources)
✅ **Delivers practical value** (teams can actually use it)
✅ **Technically sophisticated** (ML + signal processing + GPS)
✅ **Compelling narrative** ("We found why Robusto lost by 0.17s - and how to fix it")

This is a **Category 4 project with teeth** - not just dashboards, but real predictions and recommendations that could change race outcomes.

Ready to build this?
