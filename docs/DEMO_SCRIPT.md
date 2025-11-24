# RaceIQ Demo Script (3-4.5 minutes)

## Overview
This demo showcases RaceIQ's three core capabilities through a cohesive narrative flow that follows a driver's journey from real-time coaching to post-race analysis to model validation.

---

## Part 1: Race Analytics - Real-Time Coaching (90-120 seconds)

**Track:** Indianapolis Race 2
**Driver:** #89 (P8)
**Why:** Mid-pack position, shows all 5 sections clearly

### Demo Flow:

1. **Introduction** (10s)
   - "Welcome to RaceIQ - data-driven coaching for Toyota Gazoo Racing GR Cup Series"
   - "The system learns each driver's baseline from laps 1-5, then coaching starts at lap 6"

2. **Section 1: NOW - Current State** (10s)
   - Start at Lap 6
   - "At a glance: position P8, gap ahead, gap behind, last lap time"
   - "These are all ACTUAL data from completed laps - not predictions"
   - Advance to Lap 10

3. **Section 2: NEXT LAP FORECAST** (20s)
   - "This shows PREDICTED next lap time versus nearby drivers (±3 positions)"
   - "ALL BARS ARE PURPLE - no conditional coloring"
   - "Crucially: negative bars mean that driver is FASTER than you - that's a threat"
   - "Positive bars mean they're SLOWER - that's an opportunity to attack"

4. **Section 3: RACE CONTEXT - Three Plots** (35s)
   - **Gap Analysis (top):** "RED line = gap to car ahead, GREEN line = gap behind. ACTUAL measured gaps in seconds"
   - **Sector Performance (middle):** "Your LAST COMPLETED LAP vs field. GREEN = you were faster, RED = slower"
   - **Position Progression (bottom):** "Your driver in bold blue. Gold stars = battles when gap < 1 second"
   - Advance to Lap 13-15 to show progression

5. **Section 4: DIAGNOSTICS (Conditional)** (10s)
   - "When the system detects technique deviations, it flags specific issues"
   - "These only appear when there's a problem - if nothing shows, driver is performing within baseline"

6. **Section 5: RADIO MESSAGE** (10s)
   - "The actionable coaching message: 'P8 | Strong pace - push to gain positions | Focus S2'"
   - "These insights update every lap in real-time during the race"

---

## Part 2: Race Insights - Post-Race Analysis (90-120 seconds)

**Track:** Sebring Race 2
**Driver:** #51 (P9) or #63 from Race 1 (P6)
**Why:** Closest mid-pack battle (0.10s gap for #32 P9, or 0.18s for #63 P6)

### Demo Flow:

1. **Transition** (10s)
   - "After the race, let's analyze what separated drivers in close battles"
   - Navigate to **Race Insights** page
   - Select Sebring Race 2 (or Race 1)

2. **Beat-the-Driver-Ahead Analysis** (50s)
   - Select Driver #51 (P9) - only 0.10s behind P8
   - **Comparative metrics:**
     - "Gap to ahead: Just 0.10 seconds over entire race!"
     - "Pace delta: +0.007s/lap - incredibly close"
     - Show early/mid/late pace comparison
     - Tire degradation comparison
     - Traffic impact analysis

3. **AI Narrative** (30s)
   - Read excerpt from GPT-generated beat-ahead narrative:
     - "The primary factor was slower pace in early stint..."
     - Shows specific quantified differences
     - Identifies controllable vs. uncontrollable factors

4. **What-If Scenarios** (30s - OPTIONAL if time permits)
   - "What if the driver had better consistency?"
   - Show counterfactual position prediction
   - Quantified time savings and position gain potential
   - "This helps teams prioritize which skills to develop"

---

## Part 3: Model Validation - Prediction Accuracy (60-90 seconds)

**Focus:** Aggregate analysis across all 14 races

### Demo Flow:

1. **Transition** (10s)
   - "How accurate are these predictions? Let's validate across all 14 races"
   - Navigate to **Model Validation** page

2. **MAE Contour Plot** (40s)
   - **Explain axes:**
     - X-axis: Warm-up laps (data used for prediction)
     - Y-axis: Prediction horizon (laps into future)
     - Color: Mean Absolute Error (seconds)

   - **Point out key patterns:**
     - "See how error DECREASES left-to-right → more warm-up data improves predictions"
     - "Error INCREASES bottom-to-top → harder to predict far into future"
     - "Sweet spot: 3-5 warm-up laps for next-lap predictions (MAE <2s)"

3. **Performance Metrics** (20s)
   - Show aggregate statistics:
     - Overall MAE across all races
     - R² scores showing model fit
     - Position prediction accuracy (especially top-5 finishes)

4. **Per-Race Breakdown** (15s - OPTIONAL)
   - Quick scroll through per-race table
   - "Consistent performance across different tracks validates model robustness"

5. **Closing** (5s)
   - "From real-time coaching to post-race analysis to validated predictions"
   - "RaceIQ transforms telemetry data into actionable racing intelligence"

---

## Narrative Bridge Points

### Analytics → Insights Transition:
> "We've seen real-time coaching during the race. Now let's analyze what separated drivers in the final results - answering the question: **what would it take to beat the driver directly ahead?**"

### Insights → Validation Transition:
> "These insights rely on predictive models. Let's validate their accuracy across all 14 races in the GR Cup season to ensure our recommendations are trustworthy."

---

## Timing Breakdown

| Section | Min | Max |
|---------|-----|-----|
| Part 1: Race Analytics | 90s | 120s |
| Part 2: Race Insights | 90s | 120s |
| Part 3: Model Validation | 60s | 90s |
| **TOTAL** | **240s (4:00)** | **330s (5:30)** |

Target range: 3:00 - 4:30, so aim for ~210-270 seconds by:
- Cutting optional sections if running long
- Speeding up transitions
- Condensing narrative reading

---

## Key Messages to Emphasize

1. **Real-time capability** - "Sub-second predictions during live racing"
2. **Scale** - "247K telemetry samples per race, 14 races analyzed"
3. **Actionable** - "Not just data, but specific coaching recommendations"
4. **Validated** - "Predictions verified across all races"
5. **AI-powered** - "GPT-generated narratives explaining performance differences"

---

## Alternative Selections

### If Indianapolis Race 2 isn't suitable for Race Analytics:
- **Barber Race 2, Driver #55 (P2)** - Longest narrative (738 chars), top finisher
- **Indianapolis Race 1** - Has GPS data for racing line visualization (if GPS feature is demo-ready)

### If Sebring battle isn't compelling:
- **Sebring Race 1, Driver #63 (P6)** - 0.18s gap, tire degradation focus
- **Road America Race 2, Driver #15 (P8)** - 0.18s gap, also tire deg focus

---

## Technical Notes

- Ensure streamlit app is running: `streamlit run Dashboard.py`
- Pre-load both Race Analytics and Race Insights pages to avoid loading delays
- Have browser zoom set to comfortable reading level (100-110%)
- Practice transitions between pages (use sidebar navigation)
- Bookmark specific lap numbers in Race Analytics for quick navigation

---

## Backup Plan

If technical issues arise:
1. **Race Analytics loading slow:** Jump to pre-loaded lap (Lap 12 is usually safe)
2. **Telemetry plots not rendering:** Focus on coaching insights text
3. **Race Insights page errors:** Use comparative metrics table, skip visualizations
4. **Model Validation issues:** Talk through MAE concept, show any available aggregate stats
