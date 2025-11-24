# RaceCraft AI - Dashboard Design

## Overview

This document defines the user experience and visual design for the RaceCraft AI real-time coaching dashboard. The design addresses the critical gap identified in our hackathon evaluation: strong backend with no frontend.

---

## User Persona

### Primary User: Race Engineer / Team Strategist

**Context**:
- Monitoring 1-3 drivers during a race
- Limited attention bandwidth (also managing pit stops, strategy)
- Needs actionable information, not raw data
- Communication to driver via radio (brief, specific)

**Needs**:
- Quick visual scan to identify problems
- Specific actions to relay to driver
- Historical context ("is this normal for this driver?")
- Priority ranking when multiple issues arise

### Secondary User: Driver (Post-Session)

**Context**:
- Reviewing performance after race/session
- Wants to understand strengths and improvement areas
- Limited technical telemetry knowledge

**Needs**:
- Clear comparison to field
- Specific training recommendations
- Progress tracking over time

---

## Dashboard Layout

```
┌─────────────────────────────────────────────────────────────┐
│  RaceCraft AI - Indianapolis Race 1                    [⚙️] │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────┐  ┌──────────────────────────┐  │
│  │   FIELD OVERVIEW        │  │   ALERT FEED             │  │
│  │                         │  │                          │  │
│  │   #72 ██████████ P1     │  │   ⚠️ Lap 15 | #08        │  │
│  │   #08 ████████░░ P2     │  │   Brake CV +52%          │  │
│  │   #14 ███████░░░ P3     │  │   → Check fatigue        │  │
│  │   #91 ██████░░░░ P4     │  │                          │  │
│  │   ...                   │  │   ⚠️ Lap 14 | #91        │  │
│  │                         │  │   Coasting +3.2%         │  │
│  │   [State indicator]     │  │   → Commit to throttle   │  │
│  │                         │  │                          │  │
│  └─────────────────────────┘  └──────────────────────────┘  │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │   DRIVER DETAIL: #08                            [▼]  │   │
│  │                                                      │   │
│  │   PROFILE (vs Field)          STATE (vs Baseline)    │   │
│  │   ┌────────────────┐          ┌────────────────┐     │   │
│  │   │   Lift-offs    │          │   Brake CV     │     │   │
│  │   │   ████░ 1.2x   │          │   ████████░░   │     │   │
│  │   │   avg          │          │   52% ↑        │     │   │
│  │   │                │          │   (base: 35%)  │     │   │
│  │   │   G-Force      │          │                │     │   │
│  │   │   ██████ Top   │          │   Coasting     │     │   │
│  │   │   25%          │          │   ██████████   │     │   │
│  │   │                │          │   8.1% →       │     │   │
│  │   │   Full Throt.  │          │   (base: 7.9%) │     │   │
│  │   │   █████░ P8    │          │                │     │   │
│  │   └────────────────┘          └────────────────┘     │   │
│  │                                                      │   │
│  │   TREND (Last 5 Laps)                                │   │
│  │   Brake CV: 35 → 38 → 42 → 48 → 52 ↑↑                │   │
│  │   Action: Progressive degradation - consider pit     │   │
│  │                                                      │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Component Specifications

### 1. Field Overview Panel

**Purpose**: Quick scan of all drivers' current state

**Elements**:
- Driver number and position
- State health indicator (color-coded bar)
  - Green: Within baseline
  - Yellow: 1-2σ deviation
  - Red: >2σ deviation
- Click to select for detail view

**Data Source**:
- `StateMonitor.get_all_driver_states()`
- Updates each lap

### 2. Alert Feed Panel

**Purpose**: Time-ordered stream of actionable alerts

**Alert Format**:
```
[Severity Icon] Lap [N] | #[Car]
[Metric Name] [Change]
→ [Specific Action]
```

**Severity Levels**:
- 🔴 Critical: >3σ deviation, immediate action needed
- 🟡 Warning: 2-3σ deviation, monitor closely
- 🟠 Info: 1-2σ deviation, awareness only

**Alert Examples**:
```
🔴 Lap 15 | #08
Brake CV jumped to 52% (baseline: 35%)
→ Radio: "Smooth on the brakes, you're getting inconsistent"

🟡 Lap 14 | #91
Coasting up to 11.2% (baseline: 8.1%)
→ Radio: "Commit to the throttle earlier on exit"

🟠 Lap 12 | #14
Full throttle down to 61% (baseline: 65%)
→ Monitor: Check if track conditions changed
```

### 3. Driver Detail Panel

**Purpose**: Deep dive on selected driver

**Two-Column Layout**:

#### Left: Profile (vs Field)
Static traits showing driver's skill level compared to the field.

| Metric | Display | Interpretation |
|--------|---------|----------------|
| Lift-offs | `1.2x avg` | 1.2x more lift-offs than field average |
| G-Force | `Top 25%` | In top quartile for grip utilization |
| Full Throttle | `P8` | Ranks 8th in full throttle percentage |

**Visual**: Horizontal bars showing position in field distribution

#### Right: State (vs Own Baseline)
Current lap metrics compared to this driver's baseline.

| Metric | Display | Interpretation |
|--------|---------|----------------|
| Brake CV | `52% ↑` | 52% CV, above baseline (35%) |
| Coasting | `8.1% →` | 8.1%, at baseline (7.9%) |

**Visual**:
- Bar showing current value
- Baseline marker
- Trend arrow (↑ worse, → stable, ↓ better)

#### Bottom: Trend Section
- Sparkline showing last 5 laps
- Pattern detection (progressive vs sudden)
- Recommended action

---

## Alert-to-Action Mapping

Critical for hackathon: Each alert must have a specific, actionable recommendation.

### State Alerts (Real-Time)

| Alert | Action for Radio | Why It Matters |
|-------|------------------|----------------|
| Brake CV up >50% | "Smooth on the brakes, you're getting inconsistent" | Inconsistent braking = unpredictable car behavior, loss of confidence |
| Coasting up >40% | "Commit earlier on corner exit" | Coasting = lost time, indicates hesitation or fatigue |
| Both degrading | "Take a breath, reset your rhythm" | Combined degradation suggests mental fatigue |
| Sudden brake CV spike | "Check your reference points" | Sudden change often means missing a braking marker |

### Profile Recommendations (Post-Session)

| Profile Gap | Training Focus | Exercise |
|-------------|----------------|----------|
| High lift-off count | Traction management | Progressive throttle drills on skid pad |
| Low G-force utilization | Grip confidence | Gradually increase entry speed in practice |
| Low full throttle % | Commitment | Focus on earlier throttle application |

---

## Color Scheme

**Background**: Dark theme (reduces eye strain in pit/garage)
- Primary: #1a1a2e
- Secondary: #16213e

**State Indicators**:
- Good: #4ade80 (green)
- Warning: #fbbf24 (yellow)
- Critical: #ef4444 (red)
- Neutral: #6b7280 (gray)

**Accent**: #3b82f6 (blue) for selected/active elements

---

## Interaction Flow

### During Race

1. **Scan**: Engineer glances at Field Overview every few laps
2. **Alert**: Alert Feed shows new warning for #08
3. **Investigate**: Click #08 to see Driver Detail
4. **Understand**: See brake CV trend showing progressive increase
5. **Act**: Radio message to driver with specific action
6. **Monitor**: Watch next lap to see if intervention helped

### Post-Session

1. **Review**: Open Driver Detail for each driver
2. **Compare**: Look at Profile metrics vs field
3. **Plan**: Note training focus areas from recommendations
4. **Track**: Compare to previous sessions (future feature)

---

## Technical Implementation

### Frontend Options

Given hackathon timeline, recommend: **Streamlit**

**Pros**:
- Python-native (matches backend)
- Fast to build
- Good enough for demo
- Easy deployment

**Cons**:
- Not as polished as React
- Limited real-time streaming

**Alternative**: Simple HTML + Chart.js if Streamlit limitations are blocking

### Key Components to Build

1. **Dashboard page** (Streamlit layout)
   - Field overview as sidebar
   - Alert feed as main column
   - Driver detail as expandable section

2. **Data pipeline**
   - Load race data
   - Compute DriverProfile for all drivers
   - Initialize StateMonitor baselines
   - Process lap-by-lap for simulation

3. **Alert generation**
   - StateMonitor outputs alerts with severity
   - Map alerts to actions using lookup table
   - Queue for feed display

4. **Visualizations**
   - Metric bars using Streamlit progress bars
   - Trend sparklines using Plotly
   - Field distribution using Plotly histogram

---

## Demo Simulation Flow

For hackathon demo, simulate "live" race:

```python
# Pseudo-code for demo
for lap in range(1, 21):
    # Process this lap for all drivers
    for driver in drivers:
        state = state_monitor.process_lap(driver, lap)
        alerts = state_monitor.generate_alerts(state)

        for alert in alerts:
            display_alert(alert)

    # Update visualizations
    update_field_overview()
    update_driver_detail(selected_driver)

    # Pause for effect
    time.sleep(2)  # 2 seconds between laps
```

**Demo Script**:
1. Start: "Let's watch Driver #08's race unfold"
2. Laps 1-10: Baseline establishing, no alerts
3. Laps 11-13: First yellow alert (coasting up)
4. Laps 14-15: Red alert (brake CV spike)
5. Show: What engineer would radio to driver
6. End: Post-session profile recommendations

---

## Deliverable Checklist

### Minimum Viable Demo
- [ ] Field overview with state indicators
- [ ] Alert feed with 3-5 example alerts
- [ ] Driver detail panel (profile + state)
- [ ] At least one alert-to-action mapping shown
- [ ] Simulated lap-by-lap progression

### Stretch Goals
- [ ] Multiple drivers in demo
- [ ] Interactive driver selection
- [ ] Trend sparklines
- [ ] Post-session summary view
- [ ] Profile vs field distribution chart

---

## Next Steps

1. **Build DriverProfile class** - Compute profile features and state baselines
2. **Build StateMonitor class** - Detect deviations, generate alerts
3. **Create alert-action lookup** - Map all alerts to specific actions
4. **Build Streamlit dashboard** - Implement layout above
5. **Create demo script** - Simulate live race processing

Time estimate: 4-6 hours for MVP demo
