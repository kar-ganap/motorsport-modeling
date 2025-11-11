# Quantifiable Metrics: Mapping Racing Principles to Available Data

## Purpose
This document maps racing principles from `racing_fundamentals.md` and `racing_with_traffic.md` to concrete, defensible metrics that can be calculated from the available telemetry data.

---

## Available Raw Features

**Direct measurements:**
- `speed` - Vehicle speed (km/h)
- `ath` - Throttle position (0-100%)
- `pbrake_f` - Front brake pressure (bar)
- `pbrake_r` - Rear brake pressure (bar)
- `gear` - Current gear (1-6)
- `nmot` - Engine RPM
- `Steering_Angle` - Steering wheel angle (degrees)
- `accx_can` - Longitudinal acceleration (G)
- `accy_can` - Lateral acceleration (G)
- `timestamp` - Time of measurement
- `lap` - Lap number

**Derived from timing files:**
- Lap times (total, sector splits S1/S2/S3)
- Position/rank per lap
- Gap to leader/car ahead

---

## Quantifiable Principles: High Confidence

### ✅ 1. Consistency (Repeatability)

**Principle:** "Professional drivers produce repeatable laps within 0.3s"

**Metrics:**
```python
# Lap-to-lap consistency
lap_time_std = std(lap_times)
lap_time_cv = std(lap_times) / mean(lap_times)  # Coefficient of variation

# Sector consistency
s1_std = std(sector_1_times)
s2_std = std(sector_2_times)
s3_std = std(sector_3_times)

# Benchmark:
# Elite: σ < 0.3s
# Pro: σ < 0.5s
# Amateur: σ > 0.8s
```

**Data required:** ✅ Lap times, sector times (available)

**Defensibility:** ✅ Strong - Direct measurement, well-established metric in motorsport

---

### ✅ 2. Coasting Time (Efficiency)

**Principle:** "Minimize time NOT on throttle or brake - always accelerating or braking"

**Metrics:**
```python
# Define coasting as: low throttle AND low brake
coasting = (ath < 5%) AND (pbrake_f < 5 bar)

coasting_time_per_lap = sum(coasting) * sample_interval
coasting_percentage = coasting_time_per_lap / lap_time * 100

# Benchmark:
# Elite: < 5% of lap time
# Amateur: > 10% of lap time
```

**Data required:** ✅ `ath`, `pbrake_f`, `timestamp` (available)

**Defensibility:** ✅ Strong - Clear operational definition, directly measurable

---

### ✅ 3. Throttle Application Timing

**Principle:** "Get to full throttle as early as possible after apex"

**Metrics:**
```python
# Detect corner exit (minimum speed → full throttle)
corner_exit_events = detect_speed_minima()  # Local minimums in speed

for exit in corner_exit_events:
    time_to_full_throttle = timestamp[ath >= 95%] - timestamp[speed_minimum]

# Also: % of lap at full throttle
full_throttle_percentage = sum(ath > 95%) / total_samples * 100

# Benchmark:
# Elite: Time to full throttle < 2s, Full throttle % > 40%
# Amateur: Time to full throttle > 4s, Full throttle % < 30%
```

**Data required:** ✅ `ath`, `speed`, `timestamp` (available)

**Defensibility:** ✅ Strong - Corner detection is deterministic, timing is precise

---

### ✅ 4. Braking Performance

**Principle:** "Brake hard in straight line, then release progressively"

**Metrics:**
```python
# Peak brake pressure
max_brake_pressure = max(pbrake_f)

# Braking zone duration
braking_duration = time(pbrake_f > 20 bar)

# Brake release smoothness (gradient)
brake_gradient = diff(pbrake_f) / diff(timestamp)
brake_smoothness = std(brake_gradient)  # Lower = smoother

# Multiple brake applications (bad technique)
brake_pulses = count_zero_crossings(diff(pbrake_f > 20))

# Benchmark:
# Elite: Max pressure > 100 bar, pulses = 0-1 per corner
# Amateur: Max pressure < 80 bar, pulses > 2 per corner
```

**Data required:** ✅ `pbrake_f`, `timestamp` (available)

**Defensibility:** ✅ Strong - Direct measurement, clear signal processing

---

### ✅ 5. Steering Smoothness

**Principle:** "Smooth steering inputs, no sawing at the wheel"

**Metrics:**
```python
# Steering input smoothness
steering_gradient = diff(Steering_Angle) / diff(timestamp)
steering_jerk = diff(steering_gradient) / diff(timestamp)
steering_smoothness = std(steering_jerk)  # Lower = smoother

# Steering reversals (sawing)
steering_reversals = count_direction_changes(Steering_Angle)

# Benchmark:
# Elite: Low jerk, < 5 reversals per corner
# Amateur: High jerk, > 10 reversals per corner
```

**Data required:** ✅ `Steering_Angle`, `timestamp` (available)

**Defensibility:** ✅ Strong - Jerk is well-defined mathematical derivative

---

### ✅ 6. G-Force Utilization (Traction Circle)

**Principle:** "Use full grip available, approach limits of traction circle"

**Metrics:**
```python
# Combined grip usage
total_g = sqrt(accx_can² + accy_can²)

# Peak usage
max_combined_g = max(total_g)
mean_combined_g = mean(total_g[speed > 50])  # Exclude slow sections

# Traction circle efficiency (how close to theoretical limit)
traction_efficiency = mean_combined_g / theoretical_max_g  # e.g., 1.5G

# Benchmark:
# Elite: Peak > 1.8G, Mean > 1.2G
# Amateur: Peak < 1.4G, Mean < 0.9G
```

**Data required:** ✅ `accx_can`, `accy_can` (available)

**Defensibility:** ✅ Strong - Physics-based, well-established in motorsport

---

### ✅ 7. Minimum Corner Speed

**Principle:** "Carry maximum speed through corners"

**Metrics:**
```python
# Detect corners (high steering angle + lateral G)
corner_events = detect_corners(Steering_Angle, accy_can)

for corner in corner_events:
    min_speed_in_corner = min(speed[corner_start:corner_end])

# Compare across laps for same corner
corner_5_min_speeds = [87, 89, 88, 87, 90, 88]  # km/h across 6 laps
corner_5_consistency = std(corner_5_min_speeds)

# Benchmark:
# Elite: Higher min speeds, low variance (<2 km/h)
# Amateur: Lower min speeds, high variance (>5 km/h)
```

**Data required:** ✅ `speed`, `Steering_Angle`, `accy_can` (available)

**Defensibility:** ✅ Strong - Speed is direct measurement, corner detection is deterministic

---

### ✅ 8. Brake-Turn Overlap (Trail Braking)

**Principle:** "Release brake as steering input increases (trail braking)"

**Metrics:**
```python
# Correlation between brake release and steering increase
# During turn-in phase

turn_in_events = detect_turn_in()  # Steering angle starts increasing

for turn_in in turn_in_events:
    window = timestamp[turn_in:turn_in + 2s]

    # Should see: brake pressure decreasing, steering increasing
    brake_slope = linear_fit(pbrake_f[window]).slope  # Should be negative
    steering_slope = linear_fit(abs(Steering_Angle[window])).slope  # Should be positive

    trail_brake_quality = -brake_slope * steering_slope  # Higher = better coordination

# Benchmark:
# Elite: Strong negative correlation (good trail braking)
# Amateur: Zero or positive correlation (release brake, then turn)
```

**Data required:** ✅ `pbrake_f`, `Steering_Angle`, `timestamp` (available)

**Defensibility:** ✅ Strong - Temporal correlation is well-defined

---

### ✅ 9. Throttle-Steering Coordination

**Principle:** "Increase throttle as steering unwinds (inverse relationship)"

**Metrics:**
```python
# During corner exit
corner_exits = detect_corner_exit()  # Steering angle decreasing

for exit in corner_exits:
    window = timestamp[exit:exit + 3s]

    # Should see: steering decreasing, throttle increasing
    correlation = pearson_correlation(
        abs(Steering_Angle[window]),
        ath[window]
    )

# Ideal: correlation ≈ -0.8 (strong inverse)

# Also: throttle application while still turning (BAD)
simultaneous_inputs = sum((ath > 50) AND (abs(Steering_Angle) > 20))

# Benchmark:
# Elite: Strong inverse correlation, minimal simultaneous inputs
# Amateur: Weak correlation, frequent simultaneous inputs
```

**Data required:** ✅ `ath`, `Steering_Angle`, `timestamp` (available)

**Defensibility:** ✅ Strong - Correlation is standard statistical measure

---

### ✅ 10. Tire Degradation Pattern

**Principle:** "Lap times degrade predictably as tires wear"

**Metrics:**
```python
# Lap time degradation rate
lap_times = [128.5, 129.1, 129.8, 130.2, 130.9, 131.5]  # seconds
degradation_rate = linear_fit(lap_times).slope  # seconds per lap

# Sector-specific degradation
s1_degradation = linear_fit(s1_times).slope
s2_degradation = linear_fit(s2_times).slope
s3_degradation = linear_fit(s3_times).slope

# Total degradation over stint
total_degradation = lap_times[-1] - lap_times[0]

# Benchmark:
# Aggressive driving: > 0.15s/lap degradation
# Conservative: < 0.08s/lap degradation
```

**Data required:** ✅ Lap times, sector times (available)

**Defensibility:** ✅ Strong - Linear regression is well-established, widely used in F1/motorsport

---

## Quantifiable Principles: Medium Confidence

### 🟡 11. Braking Point Consistency

**Principle:** "Brake at the same point every lap"

**Metrics:**
```python
# Challenge: Without GPS, we need to infer braking point

# Method 1: Time-based (relative to sector start)
# Assume sectors start at same point each lap
sector_start_times = get_sector_start_timestamps()

for lap in laps:
    brake_onset = first_timestamp(pbrake_f > 50 bar)
    time_from_sector_start = brake_onset - sector_start

braking_point_variance = std(time_from_sector_start)

# Method 2: Speed-based
# "When speed drops from >140 km/h to <100 km/h"
for lap in laps:
    brake_event = speed.transition(140 -> 100)
    # Track timing of this transition

# Benchmark:
# Elite: < 0.1s variance in braking point
# Amateur: > 0.3s variance
```

**Data required:** ✅ `pbrake_f`, `speed`, sector timing (available)

**Limitations:** ⚠️ Without GPS, we're inferring position from time/speed
- Assumes consistent sector entry speed
- Traffic can affect this measurement

**Defensibility:** 🟡 Medium - Method is sound but has assumptions

---

### 🟡 12. Corner Entry Speed Consistency

**Principle:** "Consistent entry speed leads to consistent lap times"

**Metrics:**
```python
# Detect corner entry: high speed → braking begins
corner_entries = detect_braking_events()

for entry in corner_entries:
    entry_speed = speed[first(pbrake_f > 20)]

# Group by corner (challenging without GPS)
# Method: Use time-in-lap as proxy
# Corner 1 is always ~10s into lap, Corner 2 at ~25s, etc.

corner_1_entry_speeds = [138, 141, 139, 140, 137]  # km/h
corner_1_consistency = std(corner_1_entry_speeds)

# Benchmark:
# Elite: < 3 km/h variance
# Amateur: > 7 km/h variance
```

**Data required:** ✅ `speed`, `pbrake_f`, `timestamp` (available)

**Limitations:** ⚠️ Corner identification requires lap-time-based heuristics

**Defensibility:** 🟡 Medium - Assumes consistent lap timing (affected by traffic)

---

### 🟡 13. Gear Selection Efficiency

**Principle:** "Keep engine in power band (optimal RPM range)"

**Metrics:**
```python
# Time spent in optimal RPM range
# GR86 power band: approximately 5000-7500 RPM (estimated)

optimal_rpm_time = sum((nmot >= 5000) AND (nmot <= 7500)) / total_time * 100

# Upshift/downshift timing
# Should upshift near redline, downshift to stay in power band
for gear_change in detect_gear_changes():
    rpm_at_shift = nmot[gear_change]

upshift_rpm_avg = mean(rpm_at_upshift)
downshift_rpm_avg = mean(rpm_at_downshift)

# Benchmark:
# Elite: > 70% time in power band, upshift > 7000 RPM
# Amateur: < 50% time in power band, upshift < 6500 RPM
```

**Data required:** ✅ `gear`, `nmot` (available)

**Limitations:** ⚠️ Requires knowledge of GR86's specific power band

**Defensibility:** 🟡 Medium - Power band is car-specific, may need tuning

---

### 🟡 14. Longitudinal Load Transfer Quality

**Principle:** "Smooth transitions to avoid unsettling the car"

**Metrics:**
```python
# Rate of change in longitudinal acceleration
accx_jerk = diff(accx_can) / diff(timestamp)

# Smoothness = low jerk
accx_smoothness = std(accx_jerk)

# Detect abrupt weight transfers (bad)
harsh_events = count(abs(accx_jerk) > threshold)  # e.g., 5 G/s

# Benchmark:
# Elite: Low jerk std, < 5 harsh events per lap
# Amateur: High jerk std, > 15 harsh events per lap
```

**Data required:** ✅ `accx_can`, `timestamp` (available)

**Limitations:** ⚠️ Threshold for "harsh" is somewhat arbitrary

**Defensibility:** 🟡 Medium - Jerk is well-defined, but threshold needs validation

---

## Quantifiable Principles: Lower Confidence (Requires Assumptions)

### 🟠 15. Racing Line Precision

**Principle:** "Use full track width, hit apex consistently"

**Challenge:** ❌ No GPS data

**Possible proxy metrics:**
```python
# Indirect measure: Minimum speed variance at "apex"
# If hitting same apex, minimum speed should be consistent

corner_min_speeds = get_min_speeds_per_corner_per_lap()
apex_precision = std(corner_min_speeds)

# Lower variance → more precise apex hitting
```

**Defensibility:** 🟠 Low - This measures consequence of line precision, not line itself

---

### 🟠 16. Track Position Usage

**Principle:** "Use every centimeter of track width"

**Challenge:** ❌ No GPS/position data

**Possible proxy:**
```python
# Can't directly measure, but can infer from:
# - Higher corner speeds suggest wider line (more track used)
# - Compare to theoretical maximum

corner_speed_ratio = actual_min_speed / theoretical_min_speed
# Closer to 1.0 → better track usage
```

**Defensibility:** 🟠 Low - Many confounding factors (driver skill, tire condition, etc.)

---

### 🟠 17. Overtaking Success Rate

**Principle:** "Great drivers execute decisive overtakes"

**Challenge:** Position changes can be inferred but not directly measured

**Metrics:**
```python
# Infer from race results + timing
# If position changes between laps, overtake occurred

for lap in laps:
    if position[lap] < position[lap-1]:
        # Overtake!
        overtake_count += 1

# Also: time spent in battles (lap time variance while near another car)
# Challenge: Don't have explicit "proximity to other cars" data
```

**Defensibility:** 🟠 Low - Can detect outcome, but not quality of execution

---

### 🟠 18. Traffic Impact

**Principle:** "Great drivers minimize lap time loss in traffic"

**Metrics:**
```python
# Detect traffic laps: unusually slow lap times
# Assuming clean air baseline

clean_air_pace = median(lap_times)
traffic_laps = lap_times[lap_times > clean_air_pace + 2s]

traffic_time_loss = mean(traffic_laps) - clean_air_pace

# Challenge: Need to distinguish traffic from tire deg, driver error
```

**Defensibility:** 🟠 Low - Many confounding factors, hard to isolate traffic

---

## Non-Quantifiable Principles (Data Not Available)

### ❌ 19. Visual Reference Points
**Principle:** "Look where you want to go, not where you are"

**Why not measurable:** No eye-tracking data

---

### ❌ 20. Racing Line Geometry
**Principle:** "Wide-in, clip apex, wide-out"

**Why not measurable:** No GPS/position data

---

### ❌ 21. Actual Braking Distance
**Principle:** "Brake as late as possible"

**Why not measurable:** No position/distance markers (only time-based)

---

### ❌ 22. Pit Strategy Execution
**Principle:** "Optimal pit window timing"

**Why not measurable:** No explicit pit stop data (can infer from lap time gaps)

---

## Summary: Metrics Scorecard

| Confidence | Count | Principles |
|-----------|-------|-----------|
| ✅ High (Strong) | 10 | Consistency, Coasting, Throttle timing, Braking, Steering smoothness, G-force usage, Min corner speed, Brake-turn overlap, Throttle-steering coordination, Tire degradation |
| 🟡 Medium | 4 | Braking point consistency, Entry speed consistency, Gear efficiency, Load transfer smoothness |
| 🟠 Low | 4 | Racing line precision (proxy), Track usage (proxy), Overtaking (inference), Traffic impact (confounded) |
| ❌ Not Possible | 4+ | Visual reference, Racing line geometry, Braking distance, Direct pit strategy |

---

## Recommended Metrics for Hackathon Project

### Tier 1: Must Have (High Confidence, High Impact)
1. **Consistency Score** - σ of lap times and sector times
2. **Efficiency Score** - % time coasting, % time at full throttle
3. **Smoothness Score** - Steering jerk, brake pulse count
4. **Grip Usage Score** - Mean combined G-forces
5. **Tire Degradation Rate** - Lap time increase per lap

### Tier 2: Should Have (Medium Confidence, Good Insight)
6. **Braking Performance** - Peak pressure, smoothness
7. **Throttle Discipline** - Time to full throttle, coordination with steering
8. **Corner Speed Index** - Min speeds variance per corner

### Tier 3: Nice to Have (Lower Confidence, Interesting)
9. **Gear Optimization** - % time in power band
10. **Traffic Resilience** - Lap time variance during battles

---

## Implementation Strategy

### Phase 1: Core Metrics (Week 1)
- Implement Tier 1 metrics
- Validate on known fast/slow drivers
- Build baseline dashboard

### Phase 2: Advanced Metrics (Week 2)
- Add Tier 2 metrics
- Develop composite "Driver Skill Score"
- Create comparison visualizations

### Phase 3: Insights & Polish (Week 3)
- Identify patterns in data
- Build recommendations engine
- Polish UI/UX

---

## Validation Approach

For each metric, validate by:

1. **Sanity check:** Do race winners score better than last place?
2. **Consistency check:** Do metrics agree with each other?
3. **Domain expert review:** Do values match motorsport expectations?

**Example:**
```python
# Validate consistency metric
winner = get_driver_data(position=1)
last_place = get_driver_data(position=20)

assert winner.lap_time_std < last_place.lap_time_std
# If this fails, metric is suspect
```

---

## Final Recommendation

**Focus on the 10 high-confidence metrics.** These are:
- Defensible with clear operational definitions
- Directly measurable from available data
- Aligned with motorsport best practices
- Provide actionable insights for drivers

Avoid trying to quantify principles that require GPS or subjective assessment. Instead, use the strong metrics to build a compelling story about driver performance.

**The data you have is sufficient to build a world-class driver analysis tool** - you don't need GPS if you focus on technique quality rather than geometric racing lines.
