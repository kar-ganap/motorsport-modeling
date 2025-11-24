# Counterfactual & Comparative Analysis Implementation Plan

## Executive Summary

This document outlines two approaches for analyzing race outcomes:
1. **Counterfactual Simulation Models** - Build causal models to simulate alternative race scenarios
2. **Comparative Performance Analysis** - Compare driver performance against field benchmarks

We'll implement both, starting with #2 (comparative) as a foundation, then building #1 (counterfactual) on top.

---

## Available Data Assets

### Race-Level Data
- **Lap times**: Per-lap timing for all drivers (`vir_lap_time_R1.csv`)
- **Positions**: Race positions, gaps to leader/ahead/behind
- **Race results**: Final standings, class results
- **Weather**: Track conditions, temperature, wind

### Telemetry Data (Per-Lap or High-Frequency)
From `R1_vir_telemetry_data.csv` and similar:
- **Speed**: `speed`, `top_speed`
- **Acceleration**: `accx_can`, `accy_can` (lateral/longitudinal g-forces)
- **Braking**: `pbrake_f`, `pbrake_r` (front/rear brake pressure)
- **Throttle**: `throttle`, `ath` (throttle position %)
- **Steering**: `Steering_Angle`
- **Position**: `gps_lat`, `gps_lng`, `gps_alt` (when available)
- **Drivetrain**: `gear`, `rpm`, `wheel_speed_*`

### Computed Features
From `race1_features.parquet`:
- **Pace metrics**: `lap_time`, `rolling_avg_3`, `lap_time_diff`
- **Fuel estimation**: `fuel_load_estimate` (computed from weight)
- **Position dynamics**: `gap_delta_ahead`, `gap_delta_behind`, `is_fighting`
- **Race context**: `race_progress`, `laps_remaining`, `is_under_yellow`
- **Performance relative to field**: `field_median`, `relative_time`

### Missing Data (Would Need to Compute)
- **Tire age**: Laps since last pit stop (can infer from lap times + pit detection)
- **Tire compound**: Not available in current data
- **Pit stop history**: Need to detect from lap times / position jumps
- **Traffic density**: Can compute from position gaps
- **Corner-by-corner performance**: Need GPS + sector timing

---

## APPROACH 1: Comparative Performance Analysis

**Goal**: Compare driver's performance to field benchmarks to identify performance deltas

This is EASIER and MORE HONEST - we're not simulating what could have happened, just comparing what DID happen.

### 1.1 Pace Comparison Model

**What it answers**: "How did your pace compare to others in similar conditions?"

#### Implementation Steps:

**Step 1: Build Field Benchmarks**
```python
class FieldBenchmark:
    """
    Compute field-wide performance benchmarks for comparison.
    """
    def __init__(self, race_data: pd.DataFrame):
        self.race_data = race_data
        self.benchmarks = self._compute_benchmarks()

    def _compute_benchmarks(self) -> pd.DataFrame:
        """
        Per lap, compute field statistics:
        - Median lap time (clean laps only)
        - P25/P75 lap times (quartiles)
        - Top 5 average
        - Bottom 5 average
        """
        per_lap = []
        for lap_num in self.race_data['lap'].unique():
            lap_data = self.race_data[self.race_data['lap'] == lap_num]

            # Filter to clean laps (exclude outliers > 1.3x median)
            median_lt = lap_data['lap_time'].median()
            clean = lap_data[lap_data['lap_time'] < median_lt * 1.3]

            per_lap.append({
                'lap': lap_num,
                'field_median': clean['lap_time'].median(),
                'field_p25': clean['lap_time'].quantile(0.25),
                'field_p75': clean['lap_time'].quantile(0.75),
                'top5_avg': clean.nsmallest(5, 'lap_time')['lap_time'].mean(),
                'bottom5_avg': clean.nlargest(5, 'lap_time')['lap_time'].mean(),
            })

        return pd.DataFrame(per_lap)
```

**Step 2: Compute Driver Deltas**
```python
def compute_driver_deltas(driver_laps: pd.DataFrame, benchmarks: pd.DataFrame) -> pd.DataFrame:
    """
    For each lap, compute how driver performed vs field.
    """
    merged = driver_laps.merge(benchmarks, on='lap')

    merged['delta_vs_median'] = merged['lap_time'] - merged['field_median']
    merged['delta_vs_top5'] = merged['lap_time'] - merged['top5_avg']
    merged['percentile_rank'] = merged.apply(
        lambda row: compute_percentile(row['lap_time'], row['lap'], race_data),
        axis=1
    )

    return merged
```

**Step 3: Segment Analysis**
```python
def segment_race(race_data: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    """
    Break race into segments for targeted comparison:
    - Early stint (laps 1-5): Fresh tires
    - Mid stint (laps 6-15): Tire management
    - Late stint (lap 16+): Tire degradation
    """
    segments = {
        'early': race_data[race_data['lap'].between(1, 5)],
        'mid': race_data[race_data['lap'].between(6, 15)],
        'late': race_data[race_data['lap'] >= 16],
    }
    return segments
```

**Step 4: Generate Comparative Insights**
```python
def generate_comparative_narrative(driver_num: int, race_data: pd.DataFrame) -> str:
    """
    Create honest, comparative narrative.
    """
    driver_data = race_data[race_data['vehicle_number'] == driver_num]
    benchmarks = FieldBenchmark(race_data).benchmarks
    deltas = compute_driver_deltas(driver_data, benchmarks)

    # Early vs late comparison
    early_delta = deltas[deltas['lap'] <= 5]['delta_vs_median'].mean()
    late_delta = deltas[deltas['lap'] >= 16]['delta_vs_median'].mean()

    degradation_diff = late_delta - early_delta

    # Compare to field average degradation
    field_early = benchmarks[benchmarks['lap'] <= 5]['field_median'].mean()
    field_late = benchmarks[benchmarks['lap'] >= 16]['field_median'].mean()
    field_degradation = field_late - field_early

    if degradation_diff > field_degradation + 0.2:
        return f"""
        Driver #{driver_num} experienced {degradation_diff:.2f}s more pace drop-off
        than the field average ({field_degradation:.2f}s). This suggests:
        - Tire management opportunity: Field average shows {field_degradation:.2f}s deg
        - Potential setup issue: Excessive tire wear
        - Gap to leader could have been {(degradation_diff - field_degradation) * 10:.1f}s
          smaller with field-average tire management
        """
    elif degradation_diff < field_degradation - 0.2:
        return f"""
        Driver #{driver_num} managed tire degradation BETTER than field average.
        - Driver degradation: {degradation_diff:.2f}s
        - Field average: {field_degradation:.2f}s
        - This superior tire management gained ~{(field_degradation - degradation_diff) * 10:.1f}s
          over drivers with average management
        """
    else:
        return f"""
        Driver #{driver_num}'s tire degradation was similar to field average.
        - Performance opportunities likely in other areas (setup, traffic, mistakes)
        """
```

#### Dashboard Visualization

```python
def create_comparative_analysis_viz(driver_num, race_data):
    """
    Create comparative visualization showing:
    1. Lap time vs field median (line chart)
    2. Percentile rank over race (area chart)
    3. Stint comparison table (early/mid/late vs field)
    """

    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=('Pace vs Field Median', 'Percentile Rank Evolution')
    )

    # Plot 1: Delta vs median
    fig.add_trace(
        go.Scatter(
            x=laps,
            y=delta_vs_median,
            fill='tozeroy',
            name='Delta vs Field',
            line=dict(color='blue')
        ),
        row=1, col=1
    )

    # Add zero line
    fig.add_hline(y=0, line_dash='dash', line_color='green', row=1, col=1)

    # Plot 2: Percentile rank
    fig.add_trace(
        go.Scatter(
            x=laps,
            y=percentile_ranks,
            fill='tozeroy',
            name='Field Position %',
            line=dict(color='orange')
        ),
        row=2, col=1
    )

    return fig
```

---

### 1.2 Traffic Impact Analysis

**What it answers**: "How much did traffic cost you?"

#### Implementation Steps:

**Step 1: Detect Traffic Situations**
```python
def detect_traffic_laps(race_data: pd.DataFrame, driver_num: int) -> pd.DataFrame:
    """
    Identify laps where driver was in traffic (close gaps).
    """
    driver_laps = race_data[race_data['vehicle_number'] == driver_num].copy()

    # Traffic = gap to ahead < 1.5s OR gap to behind < 1.5s
    driver_laps['in_traffic'] = (
        (driver_laps['gap_to_ahead'] < 1.5) |
        (driver_laps['gap_to_behind'] < 1.5)
    )

    return driver_laps
```

**Step 2: Compare Traffic vs Clean Air Pace**
```python
def analyze_traffic_impact(driver_laps: pd.DataFrame, benchmarks: pd.DataFrame) -> Dict:
    """
    Compare pace in traffic vs clean air.
    """
    traffic_laps = driver_laps[driver_laps['in_traffic'] == True]
    clean_laps = driver_laps[driver_laps['in_traffic'] == False]

    traffic_delta = traffic_laps['delta_vs_median'].mean()
    clean_delta = clean_laps['delta_vs_median'].mean()

    traffic_cost = traffic_delta - clean_delta
    traffic_count = len(traffic_laps)

    total_traffic_cost = traffic_cost * traffic_count

    return {
        'traffic_laps': traffic_count,
        'cost_per_lap': traffic_cost,
        'total_cost': total_traffic_cost,
        'narrative': f"""
        Traffic cost: {total_traffic_cost:.1f}s total over {traffic_count} laps.
        Average {traffic_cost:.2f}s/lap slower in traffic vs clean air.
        Better qualifying/positioning could have avoided {total_traffic_cost:.1f}s of losses.
        """
    }
```

---

### 1.3 Stint Degradation Comparison

**What it answers**: "How did your tire degradation compare to others?"

```python
def compare_stint_degradation(driver_num: int, race_data: pd.DataFrame) -> str:
    """
    Compare driver's stint degradation pattern to field leaders.
    """
    driver_data = race_data[race_data['vehicle_number'] == driver_num]

    # Get P1-P3 for comparison
    leaders = race_data[race_data['position'].isin([1, 2, 3])]

    # Compute degradation rate (slope of lap times vs lap number)
    driver_slope = compute_degradation_slope(driver_data)
    leader_slope = leaders.groupby('vehicle_number').apply(compute_degradation_slope).mean()

    delta_slope = driver_slope - leader_slope

    if delta_slope > 0.05:  # Degrading faster than leaders
        return f"""
        Tire degradation analysis:
        - Your degradation rate: {driver_slope:.3f}s/lap
        - Leaders' average: {leader_slope:.3f}s/lap
        - Difference: {delta_slope:.3f}s/lap

        Over 20 laps, this costs ~{delta_slope * 20:.1f}s.

        Opportunities:
        - Tire management technique (smoother inputs, earlier braking)
        - Setup changes (camber, pressure, suspension)
        - Driving line optimization (avoid high-load corners)
        """
```

---

## APPROACH 2: Counterfactual Simulation Models

**Goal**: Build physics-based models to simulate alternative scenarios

This is HARDER but more powerful - allows "what if" scenarios with actual constraints.

### 2.1 Tire Degradation Model

**What it enables**: Simulate different tire strategies, driving styles

#### Model Structure:

```python
class TireDegradationModel:
    """
    Model tire performance degradation over stint.

    Based on:
    - Tire age (laps on current tires)
    - Tire load (g-forces, braking intensity)
    - Track temperature
    - Driving style (aggression metrics)
    """

    def __init__(self):
        # Fit from observed data
        self.base_degradation_rate = None  # s/lap baseline
        self.load_factor = None  # Additional deg per unit of avg g-force
        self.temp_factor = None  # Deg rate change per degree C

    def fit(self, historical_races: List[pd.DataFrame]):
        """
        Fit model parameters from historical data.

        For each driver stint:
        1. Extract lap times vs tire age
        2. Extract telemetry to compute avg g-forces
        3. Extract weather for temperature
        4. Fit: lap_time = base + (age * deg_rate) + (load * load_factor) + noise
        """
        X = []
        y = []

        for race in historical_races:
            for driver_num in race['vehicle_number'].unique():
                driver_laps = race[race['vehicle_number'] == driver_num]

                # Detect stint boundaries (pit stops = lap time > 2x median)
                stints = self._detect_stints(driver_laps)

                for stint in stints:
                    for idx, lap in stint.iterrows():
                        tire_age = lap['lap'] - stint['lap'].min()
                        avg_g = self._compute_avg_gforce(lap, telemetry)
                        temp = lap['track_temp']  # If available

                        X.append([tire_age, avg_g, temp])
                        y.append(lap['lap_time'])

        # Fit linear model
        from sklearn.linear_model import LinearRegression
        model = LinearRegression()
        model.fit(X, y)

        self.base_degradation_rate = model.coef_[0]
        self.load_factor = model.coef_[1]
        self.temp_factor = model.coef_[2]

    def predict_lap_time(self, tire_age: int, avg_g: float, temp: float, base_pace: float) -> float:
        """
        Predict lap time given tire state and driving style.
        """
        degradation = (
            tire_age * self.base_degradation_rate +
            avg_g * self.load_factor +
            temp * self.temp_factor
        )
        return base_pace + degradation

    def simulate_stint(
        self,
        base_pace: float,
        stint_length: int,
        driving_style: str = 'normal'  # 'aggressive', 'normal', 'conservative'
    ) -> List[float]:
        """
        Simulate lap times for a full stint under different driving styles.
        """
        # Adjust avg g-force based on style
        g_multipliers = {
            'aggressive': 1.1,  # 10% more cornering load
            'normal': 1.0,
            'conservative': 0.9,  # 10% less load (saving tires)
        }

        avg_g_baseline = 1.2  # Assume typical avg g-force
        avg_g = avg_g_baseline * g_multipliers[driving_style]

        lap_times = []
        for tire_age in range(stint_length):
            lt = self.predict_lap_time(tire_age, avg_g, temp=25, base_pace=base_pace)
            lap_times.append(lt)

        return lap_times
```

#### Counterfactual Scenarios:

```python
def counterfactual_tire_strategy(driver_num: int, race_data: pd.DataFrame) -> str:
    """
    Simulate: What if driver used more conservative tire management?
    """
    driver_laps = race_data[race_data['vehicle_number'] == driver_num]

    # Actual performance
    actual_total_time = driver_laps['lap_time'].sum()
    actual_degradation = driver_laps['lap_time'].iloc[-1] - driver_laps['lap_time'].iloc[0]

    # Simulate conservative strategy
    tire_model = TireDegradationModel()
    tire_model.fit(all_historical_races)

    conservative_laps = tire_model.simulate_stint(
        base_pace=driver_laps['lap_time'].iloc[0],
        stint_length=len(driver_laps),
        driving_style='conservative'
    )
    conservative_total = sum(conservative_laps)

    time_delta = conservative_total - actual_total_time

    if time_delta < 0:  # Conservative would have been faster
        return f"""
        TIRE STRATEGY COUNTERFACTUAL:

        Actual performance: {actual_total_time:.1f}s total, {actual_degradation:.2f}s degradation
        Conservative simulation: {conservative_total:.1f}s total

        WHAT IF more conservative tire management was used?
        - Potential gain: {abs(time_delta):.1f}s over the stint
        - Trade-off: Slower early laps, but better late-race pace
        - Net effect: FASTER overall by managing tire deg

        Implementation:
        - Reduce peak cornering g-forces by ~10%
        - Earlier, gentler brake application
        - Smoother throttle inputs
        """
    else:
        return f"""
        Current aggressive strategy appears optimal.
        Conservative approach would have cost {time_delta:.1f}s.
        """
```

---

### 2.2 Fuel Load Model

**What it enables**: Simulate impact of fuel-saving vs full-send strategies

```python
class FuelLoadModel:
    """
    Model lap time impact of fuel load.

    Heavier car = slower lap times (especially in corners).
    As fuel burns off, car gets lighter and faster.
    """

    def __init__(self):
        # Typical: 0.03s per kg of fuel
        self.time_per_kg = 0.03
        self.fuel_burn_rate = 1.2  # kg/lap (estimate)

    def predict_lap_time_with_fuel(self, base_pace: float, laps_completed: int) -> float:
        """
        Predict lap time accounting for fuel burn-off.
        """
        # Assume start with 25kg, burns 1.2kg/lap
        fuel_remaining = max(0, 25 - (laps_completed * self.fuel_burn_rate))
        fuel_penalty = fuel_remaining * self.time_per_kg

        return base_pace - fuel_penalty  # Lighter = faster
```

**Counterfactual**:
```python
def counterfactual_fuel_strategy(driver_num: int, race_data: pd.DataFrame) -> str:
    """
    WHAT IF driver started with less fuel but had to save more?
    """
    # This requires fuel consumption data - may not be available
    # But we can estimate from lap times + fuel load estimate

    driver_laps = race_data[race_data['vehicle_number'] == driver_num]

    # Scenario 1: Start lighter (less fuel) → faster early, risk running out
    # Scenario 2: Start heavier (more fuel) → slower early, can push harder late

    # Simulate both scenarios
    # ... (implementation)
```

---

### 2.3 Setup Optimization Model

**What it enables**: Simulate impact of setup changes on lap time

This is HARD - requires detailed telemetry correlation.

```python
class SetupOptimizationModel:
    """
    Model lap time impact of setup changes.

    Based on correlations between:
    - Downforce level (affects top speed vs cornering)
    - Suspension stiffness (affects tire contact, deg)
    - Brake balance (affects stopping distance, tire wear)
    """

    def fit(self, telemetry_data: pd.DataFrame):
        """
        Look for correlations:
        - High top speed → likely low downforce → slower corners
        - High corner speed → likely high downforce → lower straight speed
        """
        # This requires multiple setups from same driver to compare
        # May not be feasible with current data
        pass
```

---

## Implementation Roadmap

### Phase 1: Comparative Analysis (2-3 days)
**Priority: HIGH** - Delivers immediate value with existing data

- [ ] **Day 1**: Build `FieldBenchmark` class and `compute_driver_deltas()`
  - Implement per-lap field statistics
  - Add percentile ranking
  - Create stint segmentation

- [ ] **Day 2**: Traffic impact analysis
  - Detect traffic situations (gap < 1.5s)
  - Compare traffic vs clean air pace
  - Quantify traffic cost

- [ ] **Day 3**: Dashboard integration
  - Add comparative analysis section to Race Analytics page
  - Create visualizations (delta vs median, percentile rank)
  - Generate comparative narratives

**Output**: Dashboard shows "You were X.Xs slower than field median in late stint, vs only X.Xs slower early. Leaders maintained X.Xs deg, you had X.Xs."

### Phase 2: Simple Counterfactual Models (3-5 days)
**Priority: MEDIUM** - Adds simulation capability

- [ ] **Day 1-2**: Tire degradation model
  - Fit degradation rate from historical data
  - Add load factor (g-force correlation)
  - Validate on held-out races

- [ ] **Day 3-4**: Fuel load model
  - Estimate fuel consumption from lap time trends
  - Model weight impact on lap time
  - Simulate different fuel strategies

- [ ] **Day 5**: Integration
  - Add "Simulate Conservative Strategy" button
  - Show projected lap times under different approaches
  - Compare simulated vs actual outcomes

**Output**: Dashboard allows toggling between strategies, shows "If you had saved tires, projected total time: X.X, delta: +/- Y.Ys"

### Phase 3: Advanced Counterfactuals (Future)
**Priority: LOW** - Requires more data/validation

- [ ] Setup optimization model (needs multi-setup data)
- [ ] Pit strategy optimizer (needs pit stop data)
- [ ] Weather impact model (needs more weather granularity)

---

## Success Metrics

### For Comparative Analysis:
- ✅ User can see their pace vs field median per lap
- ✅ User can see percentile rank evolution
- ✅ Narrative explains performance deltas with field context
- ✅ Traffic cost quantified in seconds
- ✅ Honest, data-driven insights (no speculation)

### For Counterfactual Models:
- ✅ Model predictions match actual outcomes within 5% error
- ✅ Simulated strategies are physically plausible (no magic gains)
- ✅ Clear explanation of trade-offs (e.g., "save tires early → faster late")
- ✅ User can toggle between scenarios and see impact

---

## Technical Architecture

```
src/motorsport_modeling/
├── analysis/
│   ├── comparative/
│   │   ├── field_benchmark.py      # FieldBenchmark class
│   │   ├── driver_deltas.py        # compute_driver_deltas()
│   │   ├── traffic_analysis.py     # Traffic impact detection
│   │   └── stint_comparison.py     # Stint-by-stint comparison
│   │
│   └── counterfactual/
│       ├── tire_model.py           # TireDegradationModel
│       ├── fuel_model.py           # FuelLoadModel
│       ├── setup_model.py          # SetupOptimizationModel
│       └── simulator.py            # Run counterfactual scenarios
│
└── visualization/
    ├── comparative_charts.py       # Delta vs median, percentile rank
    └── counterfactual_charts.py    # Simulated scenario comparison
```

---

## Data Requirements

### What We Have:
✅ Lap times (all drivers)
✅ Position/gap data
✅ High-frequency telemetry (speed, g-forces, brake, throttle)
✅ Top speed per lap
✅ Fuel load estimates

### What We Need (Can Compute):
- Tire age (detect pit stops from lap times)
- Traffic situations (from gap data)
- Field benchmarks (aggregate statistics)
- Stint boundaries (pit stop detection)

### What We're Missing (Nice to Have):
- Tire compound data
- Actual fuel consumption
- Track temperature (per sector)
- Setup parameters (downforce, suspension)

---

## Next Steps

1. **User Decision**: Which approach to prioritize?
   - Option A: Start with Comparative (Phase 1) - faster, honest, immediate value
   - Option B: Build Counterfactual first (Phase 2) - harder, more impressive
   - Option C: Do both in parallel (riskier, slower)

2. **Validate Assumptions**: Run exploratory analysis
   - Check if tire degradation is visible in data
   - Check if fuel load estimates are reasonable
   - Check if field benchmarks are stable

3. **Build MVP**:
   - Comparative: Field benchmark + delta visualization
   - Counterfactual: Simple tire model + one scenario

4. **Iterate**: Add more models, refine narratives, validate predictions
