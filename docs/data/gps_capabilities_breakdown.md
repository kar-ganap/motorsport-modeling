# GPS Capabilities: Detailed Breakdown & Usage Plan

## Overview

GPS data (lat/long coordinates) unlocks **spatial analysis** that's impossible with timing data alone. But not all GPS capabilities are equally important for our project.

---

## Capability 1: Visual Racing Line Analysis 🎨

### What It Means

**Plot actual driving lines on track**

Instead of showing "lap time graphs" (temporal), we show "where the car actually went" (spatial).

```python
# Extract GPS for one driver, one lap
driver_55_lap_7 = gps_data[
    (gps_data['vehicle_number'] == 55) &
    (gps_data['lap'] == 7)
]

lat = driver_55_lap_7['VBOX_Lat_Min']
lon = driver_55_lap_7['VBOX_Long_Minutes']

# Plot the actual path the car took
plt.plot(lon, lat)
plt.title("Car #55 - Lap 7 - Actual Racing Line")
```

**Output:** A 2D trace showing exactly where the car drove around the track.

### The "Wow" Part

**Compare fast vs slow drivers visually**

Overlay multiple drivers' GPS traces to see WHERE they differ:

```python
# Winner's line
plt.plot(driver_55_gps['lon'], driver_55_gps['lat'],
         color='green', label='#55 Winner (1:39.7)', linewidth=3)

# Runner-up's line
plt.plot(driver_2_gps['lon'], driver_2_gps['lat'],
         color='red', label='#2 Runner-up (1:40.3)', linewidth=2, alpha=0.7)

plt.legend()
plt.title("Racing Line Comparison - Turn 5")
```

**What you see:**
```
Turn 5 (left-hander):

Green line (winner):  ──────┐
                            │  ← Wider entry
                            ↓
                            • ← Later apex
                          ↗
                        ↗ ← Uses full exit width
                      ↗

Red line (runner-up): ────┐
                          │  ← Tighter entry
                          ↓
                          • ← Earlier apex
                         ↗
                       ↗ ← Doesn't use full width
```

**Insight:** "Winner takes a wider, later line through T5 → higher exit speed → gains 0.2s on the straight"

### Color by Speed (Advanced)

Make the line color represent speed at each point:

```python
plt.scatter(lon, lat, c=speed, cmap='viridis', s=1)
plt.colorbar(label='Speed (km/h)')
```

**What you see:**
- Blue = slow (corners)
- Green = medium
- Yellow/Red = fast (straights)

**Insight:** "Winner is yellow (faster) through T5 exit while runner-up is green (slower)"

---

### **OUR USAGE: ✅ YES - Core Demo Feature**

**Why:**
- Visual "wow factor" for demo
- Immediately shows WHERE time is gained/lost
- Validates our technique metrics (does better braking → better line?)

**Implementation Priority:** Week 2
**Complexity:** Medium (GPS parsing + matplotlib/plotly)
**Impact:** High (judges will love this visual)

---

## Capability 2: Precise Corner Identification 📍

### What It Means

**No more time-based heuristics**

**Without GPS:**
```python
# Guess corners based on time
# "Corner 5 is probably around 45 seconds into the lap"
corner_5_data = telemetry[(timestamp > lap_start + 45) &
                          (timestamp < lap_start + 50)]
# ← Very imprecise! What if traffic/yellow flag changes timing?
```

**With GPS:**
```python
# Find all speed minima in GPS space
from scipy.signal import find_peaks

# Get all laps' GPS traces
all_laps_gps = get_all_laps_gps(driver)

# Find speed minima (corners) in lat/lon space
corners = []
for lap in all_laps_gps:
    # Find local minima in speed
    minima_idx = find_peaks(-lap['speed'])[0]

    for idx in minima_idx:
        corners.append({
            'lat': lap['lat'][idx],
            'lon': lap['lon'][idx],
            'speed': lap['speed'][idx]
        })

# Cluster to identify unique corners
from sklearn.cluster import DBSCAN
corner_clusters = DBSCAN(eps=0.0001).fit(corners[['lat', 'lon']])

# Now we know: Corner 5 is at (39.7953, -86.2351) ← EXACT location
```

**The power:** Every lap, every driver, we know EXACTLY which corner we're analyzing.

### **Know exactly which corner is which**

**Without GPS:**
- "I think this is Turn 5 based on timing"
- Different drivers have different lap times → different timing
- Can't compare corners across drivers reliably

**With GPS:**
```python
# Define corners by GPS coordinates
corners = {
    'T1': {'lat': 39.7954, 'lon': -86.2387, 'name': 'Turn 1'},
    'T2': {'lat': 39.7941, 'lon': -86.2365, 'name': 'Turn 2'},
    # ...
    'T5': {'lat': 39.7953, 'lon': -86.2351, 'name': 'Turn 5'},
}

# For any GPS point, find closest corner
def identify_corner(lat, lon):
    min_dist = float('inf')
    closest_corner = None

    for corner_name, corner_loc in corners.items():
        dist = haversine(lat, lon, corner_loc['lat'], corner_loc['lon'])
        if dist < min_dist:
            min_dist = dist
            closest_corner = corner_name

    return closest_corner

# Now: "This telemetry sample is at Turn 5" ← 100% certain
```

### **Measure apex positioning accuracy**

**Question:** Is the driver hitting the ideal apex consistently?

```python
# Define ideal apex for Turn 5 (from winner's fastest lap)
ideal_apex_T5 = {
    'lat': 39.79534,
    'lon': -86.23512
}

# For each lap, find where driver actually hit apex
for lap in driver.laps:
    # Find minimum speed point in Turn 5 region
    t5_data = lap.gps[is_in_turn_5(lap.gps)]
    actual_apex_idx = t5_data['speed'].idxmin()
    actual_apex = {
        'lat': t5_data['lat'][actual_apex_idx],
        'lon': t5_data['lon'][actual_apex_idx]
    }

    # Calculate deviation from ideal
    deviation = haversine(ideal_apex_T5, actual_apex)

    print(f"Lap {lap.num}: Apex deviation = {deviation:.2f} meters")

# Output:
# Lap 5:  1.2m early
# Lap 10: 0.5m perfect ✓
# Lap 15: 2.3m early  ← Inconsistent! Driver fatiguing?
```

**Insight:** Apex consistency correlates with lap time consistency.

---

### **OUR USAGE: ✅ YES - Essential for Analysis**

**Why:**
- Needed to identify corners for technique analysis
- Validates that we're comparing "apples to apples"
- Enables per-corner metric calculation

**Implementation Priority:** Week 2 (prerequisite for GPS viz)
**Complexity:** Medium (clustering algorithm, distance calculations)
**Impact:** High (makes all other GPS features possible)

**How we'll use it:**
```python
# Instead of "analyze lap 7 somewhere around 45 seconds in"
# We do "analyze Turn 5 performance across all laps"

turn_5_performance = []
for lap in driver.laps:
    t5_telemetry = get_telemetry_at_corner(lap, corner='T5')
    metrics = calculate_corner_metrics(t5_telemetry)
    turn_5_performance.append(metrics)

# Now we can say: "Driver's Turn 5 minimum speed degraded from 88km/h to 85km/h"
```

---

## Capability 3: Track Width Usage 📏

### What It Means

**See if drivers use full track width**

Racing principle: "Use every centimeter of track" (wide-in, inside-out, wide-out)

**With GPS, we can measure this directly:**

```python
# For Turn 5, find all GPS points from all drivers
all_t5_points = get_all_corner_gps(corner='T5', all_drivers=True)

# Find track boundaries (outermost points drivers reached)
track_left_edge = max(all_t5_points['lat'])   # Northernmost point
track_right_edge = min(all_t5_points['lat'])  # Southernmost point
track_width = haversine(track_left_edge, track_right_edge)

print(f"Turn 5 track width: {track_width:.1f} meters")

# For each driver, measure how much they use
for driver in drivers:
    driver_t5 = get_corner_gps(driver, corner='T5')

    driver_left = max(driver_t5['lat'])
    driver_right = min(driver_t5['lat'])
    driver_width_used = haversine(driver_left, driver_right)

    usage_pct = driver_width_used / track_width * 100

    print(f"Driver #{driver.number}: Uses {usage_pct:.1f}% of track width")

# Output:
# Driver #55 (winner):    95% ✓
# Driver #2 (runner-up):  82% ← Not using full width!
```

### **Measure lateral positioning**

**Where exactly is the car within the track width?**

This gets complex because you need:
1. Track centerline reference
2. Perpendicular distance from centerline
3. Track width at each point (varies by corner radius)

```python
# Simplified version: Distance from "ideal line"
ideal_line = get_ideal_racing_line(corner='T5')  # From fastest lap

for point in driver_lap.gps:
    # Find closest point on ideal line
    closest_ideal_point = find_nearest(ideal_line, point)

    # Calculate perpendicular distance
    lateral_deviation = haversine(point, closest_ideal_point)

    # Positive = outside ideal line, Negative = inside
    deviation_sign = calculate_side(point, ideal_line)

    lateral_position = lateral_deviation * deviation_sign

# Visualize
plt.plot(lap.distance, lap.lateral_position)
plt.title("Lateral Position Relative to Ideal Line")
```

### **Validate racing line principles**

**Question:** Do drivers who follow "wide-in, late-apex, wide-out" actually go faster?

```python
# Classify each driver's line for Turn 5
for driver in drivers:
    t5_entry = get_gps(driver, 'T5_entry')
    t5_apex = get_gps(driver, 'T5_apex')
    t5_exit = get_gps(driver, 'T5_exit')

    # Measure entry width (distance from inside edge)
    entry_width_pct = calculate_track_position(t5_entry)

    # Measure apex timing (early vs late)
    apex_position = calculate_apex_position_on_arc(t5_apex)

    # Measure exit width
    exit_width_pct = calculate_track_position(t5_exit)

    # Classify
    if entry_width_pct > 80 and apex_position > 0.6 and exit_width_pct > 80:
        classification = "Late apex, wide line (IDEAL)"
    else:
        classification = "Suboptimal line"

    # Correlate with lap time
    print(f"Driver #{driver.num}: {classification} → T5 time: {driver.t5_time}")

# Statistical test: Does "ideal line" correlate with faster times?
from scipy.stats import pearsonr
correlation, p_value = pearsonr(ideal_line_scores, corner_times)
```

---

### **OUR USAGE: ⚠️ MAYBE - Nice to Have, Not Essential**

**Why include:**
- Validates racing fundamentals (theory matches practice)
- Could find "low-hanging fruit" improvements
- Adds depth to analysis

**Why skip:**
- Complex to implement correctly (need track geometry model)
- Requires assumptions about track boundaries
- Less actionable than technique metrics
- Time-consuming

**Decision:**
- **Phase 1 (Week 2):** Skip - focus on racing line visualization only
- **Phase 2 (Stretch goal):** Add if time permits

**Alternative approach (simpler):**
```python
# Just show the spread of GPS points visually
# Let viewer judge if full width is used

plt.scatter(all_drivers_gps['lon'], all_drivers_gps['lat'],
            c='lightgray', alpha=0.3, label='All drivers')
plt.scatter(winner_gps['lon'], winner_gps['lat'],
            c='green', label='Winner')

# Visual inspection: Does winner use wider area than others?
```

---

## Capability 4: Physics-Based Simulation ⚙️

### What It Means

**Extract real track geometry from GPS**

Build a mathematical model of the track:

```python
# Collect GPS from all drivers, all laps
all_gps = load_all_gps_data()

# Statistical centerline: median lat/lon at each distance point
distance_bins = np.arange(0, track_length, step=10)  # Every 10 meters

centerline = []
for dist in distance_bins:
    # Find all GPS points near this distance
    points_at_dist = all_gps[abs(all_gps['distance'] - dist) < 5]

    # Median position = track centerline
    center_lat = np.median(points_at_dist['lat'])
    center_lon = np.median(points_at_dist['lon'])

    centerline.append({'distance': dist, 'lat': center_lat, 'lon': center_lon})

# Now we have track geometry!
```

**Calculate corner radii:**

```python
# For each corner, fit a circle to the GPS points
for corner in corners:
    corner_gps = get_corner_gps(corner)

    # Fit circle using least squares
    center, radius = fit_circle(corner_gps['lat'], corner_gps['lon'])

    corner['radius_m'] = radius * 111139  # Convert degrees to meters

    print(f"{corner['name']}: Radius = {corner['radius_m']:.1f}m")

# Output:
# Turn 1: Radius = 45m (tight hairpin)
# Turn 5: Radius = 120m (fast sweeper)
```

### **Run realistic lap simulations**

Use track geometry + vehicle dynamics to predict ideal lap time:

```python
# Vehicle model (GR86 specs)
vehicle = {
    'mass': 1200,              # kg
    'power': 228,              # hp
    'max_lateral_g': 1.5,      # G
    'max_brake_g': 1.3,        # G
}

# Simulate lap
simulated_lap = []

for segment in track_geometry:
    if segment['type'] == 'straight':
        # Accelerate to top speed
        v_exit = calculate_straight_exit_speed(
            v_entry=segment['v_entry'],
            length=segment['length'],
            power=vehicle['power']
        )
        time = calculate_straight_time(v_entry, v_exit, length)

    elif segment['type'] == 'corner':
        # Maximum speed limited by lateral G
        v_max = sqrt(vehicle['max_lateral_g'] * g * segment['radius'])

        # Brake from entry speed to corner speed
        brake_time = calculate_brake_time(v_entry, v_max, vehicle['max_brake_g'])

        # Navigate corner at v_max
        corner_time = segment['arc_length'] / v_max

        time = brake_time + corner_time

    simulated_lap.append({'segment': segment, 'time': time})

total_time = sum([s['time'] for s in simulated_lap])
print(f"Simulated ideal lap time: {total_time:.3f}s")
```

### **Generate ideal trajectories with spatial accuracy**

Optimize the racing line mathematically:

```python
from scipy.optimize import minimize

def lap_time(racing_line, track_geometry, vehicle_model):
    # Calculate lap time for a given racing line
    # (This is a complex optimization problem)
    ...
    return total_time

# Optimize
ideal_line = minimize(
    lap_time,
    initial_guess=centerline,
    args=(track_geometry, vehicle_model),
    constraints=[stay_within_track_bounds]
)

print(f"Optimal lap time: {lap_time(ideal_line):.3f}s")
```

---

### **OUR USAGE: ❌ NO - Out of Scope**

**Why it's powerful:**
- Could generate truly optimal lap (not just "best human")
- Physics-based, defensible
- Could simulate car setup changes

**Why we're skipping:**
- **Too complex for 3-week hackathon**
- Requires accurate vehicle dynamics model (don't have GR86 data)
- Requires track surface model (banking, grip levels)
- Our goal is analyze real drivers, not simulate optimal

**Our alternative:**
- Use fastest real lap as "ideal" benchmark
- Compare other drivers to that real ideal
- Much simpler, still valuable

---

## Summary: What We're Actually Using

| GPS Capability | Priority | Usage | Complexity | Impact |
|----------------|----------|-------|------------|---------|
| **1. Visual Racing Line** | ✅ HIGH | Overlay multiple drivers' lines, color by speed | Medium | Very High (wow factor) |
| **2. Corner Identification** | ✅ HIGH | Identify corners precisely, enable per-corner analysis | Medium | High (enables other features) |
| **3. Track Width Usage** | ⚠️ MAYBE | Visual inspection only (not quantitative) | Low | Medium (nice to show) |
| **4. Physics Simulation** | ❌ SKIP | Not doing - using real fastest lap as ideal | Very High | Low (for our goals) |

---

## Our GPS Usage Plan

### Week 2: GPS Implementation

**Day 1-2: Data Extraction**
```python
# Parse GPS from telemetry
gps_data = telemetry[telemetry['telemetry_name'].isin([
    'VBOX_Lat_Min',
    'VBOX_Long_Minutes',
    'Laptrigger_lapdist_dls'
])]

# Pivot to wide format
gps_wide = gps_data.pivot_table(
    index=['timestamp', 'vehicle_number', 'lap'],
    columns='telemetry_name',
    values='telemetry_value'
).reset_index()

# Clean and validate
gps_wide = gps_wide.dropna()  # Remove rows missing GPS
```

**Day 3-4: Corner Identification**
```python
# Find corners using speed minima + GPS clustering
corners = identify_corners(gps_wide)

# Validate: Should find ~14-17 corners for Indy road course
print(f"Identified {len(corners)} corners")

# Name them
corner_names = assign_corner_names(corners)
```

**Day 5-7: Visualization**
```python
# Basic racing line plot
plot_racing_line(driver_55, lap=7)

# Comparison plot (winner vs runner-up)
plot_comparison(
    driver_a=55,  # Winner
    driver_b=2,   # Runner-up
    lap=7,        # Fastest lap
    color_by='speed'
)

# Interactive plot (plotly for demo)
create_interactive_map(
    drivers=[55, 2, 13],  # Top 3
    lap=7,
    features=['speed', 'throttle', 'brake']
)
```

### GPS Features in Final Demo

**Feature 1: Track Overview**
- Show track outline (from GPS centerline)
- Mark corner locations
- Show sector boundaries

**Feature 2: Racing Line Comparison**
- Winner vs. runner-up overlay
- Color-coded by speed
- Zoom into key corners (Turn 5, Turn 8)

**Feature 3: Corner-by-Corner Analysis**
- For each corner, show:
  - Multiple drivers' lines
  - Entry/apex/exit speeds
  - Time deltas
- Highlight where winner gains time

**Feature 4: Lap Animation** (stretch goal)
- Animated replay of lap
- Show cars moving around track
- Update speed/position in real-time

---

## The "Wow" Moment Using GPS

**Demo Script:**

"Let's see WHY Spike Kohlbecker (#55) beat Will Robusto (#2) by 0.17 seconds..."

*[Switch to GPS visualization]*

"Here's the Indianapolis road course with both drivers' racing lines from their fastest laps..."

*[Show overlay - green line (winner) vs red line (runner-up)]*

"Notice anything different at Turn 5?"

*[Zoom into Turn 5]*

"The winner (green) takes a WIDER entry, hits a LATER apex, and uses the FULL track width on exit. The runner-up (red) turns in earlier and doesn't use the outside curbing."

"Let's see the speed difference..."

*[Add speed coloring - winner is yellow through corner exit, runner-up is green]*

"The winner exits Turn 5 at 142 km/h while the runner-up is only at 136 km/h - a 6 km/h difference!"

"This 6 km/h delta carries down the entire straight, gaining approximately 0.15 seconds - nearly the entire margin of victory."

*[Show technique metrics]*

"Our system detected that the runner-up's throttle application was 0.8 seconds later than the winner's at Turn 5. With real-time coaching, this is correctable!"

**Result:** Judges see visual proof + technique metrics + actionable recommendation = complete story

---

## Final Answer to Your Question

**Which aspects are we using?**

✅ **Using (Core Features):**
1. Visual racing line overlay (multiple drivers)
2. Corner identification (precise location-based)
3. Speed-colored GPS traces
4. Per-corner performance analysis

⚠️ **Maybe (If Time):**
3. Track width usage (visual inspection only)
4. Animated lap replay (cool but not essential)

❌ **Not Using (Out of Scope):**
4. Physics-based simulation (too complex)
4. Optimal trajectory generation (not needed)

The GPS features we ARE using directly support our core value proposition: **showing WHERE and WHY drivers gain/lose time, with visual proof and actionable recommendations.**

Does this clarify the GPS strategy?
