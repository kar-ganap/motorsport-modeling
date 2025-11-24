# RaceIQ: From "Push Harder" to Actionable Insights

## The Problem We Saw

Professional race coaches today face a paradox: they have gigabytes of high-resolution telemetry data, but when it comes to giving feedback, they're stuck with vague advice like "push harder" or "find more time in the corners." **The data exists. The insights don't.**

We built RaceIQ to solve this: a system that transforms raw telemetry into specific, quantified, actionable coaching—because a professional driver doesn't need to be told to try harder. They need to know *exactly* what's costing them positions and *exactly* how many seconds they can gain by fixing it.

---

## The Journey: Three Big Ideas

### 1. **Know Why You Lost—To the Driver Who Beat You**

Traditional race analysis compares drivers to field averages. That's statistically interesting but strategically useless. If you finished P5, you don't care about being 0.3s/lap slower than the median—**you care about the 2.1 seconds you lost to P4**.

We built **Beat-the-Driver-Ahead Analysis**: every driver is compared to the specific person directly ahead of them in the results. The question changes from "How did the race go?" to **"What one thing cost me this position?"**

Example from VIR:
> Driver #11 (P10) lost to #42 (P9) by 15.4s primarily through tire degradation. Their pace delta was +0.71s/lap in the late stint compared to only +0.11s/lap early race, indicating degradation cost ~10 seconds total.

This isn't academic analysis—it's a to-do list for the next race.

### 2. **Separate "Who You Are" from "What's Happening"**

Early in development, we hit a puzzle: some performance metrics (like brake smoothness) stayed remarkably consistent for each driver across 20 laps. Others (like lap-to-lap consistency) varied wildly within the same driver.

This led to a breakthrough insight: **metrics naturally partition into two categories:**

- **Profile Metrics** (high cross-driver variance, low within-driver variance): Define a driver's baseline skill. Used for pre-race setup and long-term development.
- **State Metrics** (high within-driver variance): Detect real-time changes during a race. Used for live coaching alerts.

We validated this with variance analysis across all 14 races, then architected the entire coaching system around this partition:

```
Baseline (laps 1-5) → Build Driver Profile → Monitor deviations during race → Alert when state degrades
```

Real coaching systems need both: knowing *who a driver is* (profile) and detecting *when something changes* (state).

### 3. **"What If" Isn't Speculation—It's Math**

Post-race debriefs often devolve into speculation: "If we had better tire management, we might have gained a few positions..."

We made this concrete with **Counterfactual Analysis**: machine learning models trained on 14 races that answer "what if" questions with predicted final positions:

- What if you matched top-5 tire degradation? → Predicted P8 (gain 2 positions)
- What if you matched median consistency? → Predicted P9 (gain 1 position)
- What if you had zero traffic? → Predicted P10 (no change)

**Recommendation:** Focus on tire management (+2 positions) not traffic avoidance (marginal impact).

These aren't guesses—they're validated predictions with measurable position changes.

---

## Technical Challenges We Solved

### Challenge 1: When Your Metrics Lie to You

**The Problem:** We implemented standard telemetry metrics (brake smoothness, throttle timing) and validated them against lap times. Result: **2 of 4 metrics had the WRONG correlation direction**.

- **Brake oscillations**: We assumed smooth = fast. Wrong. Fast drivers showed *more* oscillations due to trail braking.
- **Throttle timing**: We assumed faster throttle application = better. Wrong. Progressive application is actually faster.

**The Fix:** Deep dive into industry research (F1 telemetry papers, OptimumG, RACER magazine) revealed validated patterns:
- **Lift-off count**: Number of throttle decreases during acceleration (wheelspin indicator)
- **Full throttle %**: Time at >90% throttle (F1 uses this officially)
- **Brake pressure CV**: Consistency of peak pressures, not smoothness of application

**Learning:** Physics intuition beats general intuition, but empirical validation beats both. We now validate every metric with both within-driver correlation (does it predict their lap time changes?) and cross-driver correlation (does it differentiate skill levels?).

### Challenge 2: The Profile vs. State Discovery

**The Problem:** After fixing our metrics, we noticed something odd: `lift_off_count` worked great for comparing drivers but poorly for tracking a single driver's degradation. Meanwhile, `brake_cv` did the opposite.

**The Investigation:** We ran variance analysis on all metrics:

```python
# Within-driver variance: How much does this metric change for one driver?
# Cross-driver variance: How different are drivers from each other?

lift_off_count: cross/within ratio = 1.66 (stable within driver, differentiates across)
brake_cv:       cross/within ratio = 0.48 (varies within driver, similar across)
```

**The Insight:** These aren't broken metrics—they're measuring different things:
- **Profile features** (ratio > 1.5): Skill traits like traction management
- **State features** (ratio < 0.7): Fatigue signals like braking degradation

**Impact:** This wasn't our original design—it *emerged from the data*. We restructured the entire coaching system around this discovery, leading to two distinct recommendation flows:
- Profile: "Your lift-offs are 2x field average → Focus on progressive throttle"
- State: "Brake CV up 50% from your baseline → Check fatigue"

### Challenge 3: Finding the Bug That Made Predictions Impossible

**The Problem:** Our lap time predictor had RMSE of 23.58 seconds—far worse than "just predict the average." Clearly something was fundamentally broken.

**The Hunt:** We suspected data leakage. After systematic debugging:

```python
# THE BUG (in feature_engineering.py:240-287):
df['rolling_avg_3'] = x.rolling(window=3, min_periods=1).mean()
# ☝️ This includes the CURRENT lap in the rolling average!

df['prev_lap_time'] = df['prev_lap_time'].fillna(df['lap_time'])
# ☝️ First lap "previous" time is filled with... the current lap time

# THE FIX:
df['rolling_avg_3'] = x.shift(1).rolling(window=3, min_periods=1).mean()
df['prev_lap_time'] = df['prev_lap_time']  # Leave NaN for first lap
```

**Additional Discovery:** Even after fixing leakage, absolute lap time prediction remained poor (RMSE ~6s). Root cause: race events (yellow flags, restarts) cause 40-50 second variations that affect all drivers equally and can't be predicted from prior laps.

**The Pivot:** Switch from predicting `lap_time` to predicting `relative_performance = lap_time - field_median`. This normalizes out race events.

**Result:** 3.7x RMSE improvement (from 6.5s to 1.8s for normal laps). Simple models (`0.3 * prev_relative + 0.7 * driver_mean`) outperformed complex gradient boosting—sometimes less is more.

### Challenge 4: Multi-Format Data Pipeline

The GR Cup dataset isn't uniform. We found:
- **Indianapolis/VIR:** Long-format CSV (signal, value pairs)
- **Barber/Mid-Ohio:** Wide-format CSV (columns per signal)
- **Sebring:** Nested JSON with lap 32768 corruption bug

We built an adaptive loader that:
1. Auto-detects format by inspecting the first few rows
2. Handles missing GPS data gracefully (VIR, Barber, Mid-Ohio)
3. Filters corrupt laps (Sebring's lap 32768 issue)
4. Normalizes signal names (`pbrake_f` vs `brake_pressure`)

**Result:** Load any track/race combination with a single API call. Validated across all 7 tracks × 2 races = 14 datasets.

---

## What We Learned

### Insight 1: When More Features Hurt Performance

Counter-intuitively, our best position prediction model uses just 2 features:
- Previous lap's relative performance (30% weight)
- Driver's average relative performance (70% weight)

We tried adding:
- Position/gap features (no improvement)
- Complex telemetry features (slight degradation)
- Gradient boosting with 10+ features (worse than linear model)

**Why?** With high-variance race events and limited training data, simpler models that capture the core signal (driver ability + momentum) beat complex models that overfit noise.

### Insight 2: Controllable Consistency vs. Raw Consistency

Standard lap time consistency (σ of lap times) has a fatal flaw: it can't distinguish between "driver pushed too hard" vs. "driver caught traffic."

We built **controllable consistency**: exclude laps where speed traces show traffic interactions (identified by sector-level speed drops that don't correlate with braking).

**Impact:** This single metric improved position prediction accuracy by 12% and reduced correlation with random race events.

### Insight 3: Data Quality Beats Data Quantity

We started thinking we needed GPS racing lines for every track. Reality: GPS data was only available for 2 of 7 tracks, and the insights we *could* extract (racing line comparison, track position) didn't improve position predictions as much as telemetry-based features like tire degradation.

**Lesson:** Deep analysis of available data beats shallow analysis of perfect data.

---

## The Stack

**Data Processing:**
- pandas for telemetry manipulation (247k rows/race)
- Custom variance-based feature partitioning
- Linear regression for degradation, gradient boosting for positions

**Dashboard:**
- Streamlit multi-page architecture (3 specialized pages)
- Plotly for interactive charts
- Lazy loading with session state management

**AI Integration:**
- GPT-4o via OpenAI API
- Structured prompts with system/user separation
- Precomputed narratives (14 races × ~25 drivers = 350 analyses cached)

**Deployment:**
- uv for dependency management
- Parquet for compressed analytics storage (~2MB/race vs 500MB CSV)
- Local setup with clear instructions for judges

---

## Impact: Real Numbers

**Coverage:**
- 14 races analyzed (7 tracks × 2 races)
- ~350 driver performances evaluated
- 247,000 telemetry samples per race processed

**Performance:**
- Position predictions: MAE < 2 positions on cross-validation
- Lap time predictions: RMSE 1.8s for normal racing laps
- Counterfactual scenarios: 4 per driver (tire degradation, consistency, traffic, combined)
- Real-time alerts: Sub-second latency during lap-by-lap simulation

**Model Validation:**
- Metric validation: 4/6 metrics show expected correlation with lap time
- Profile/State partition: Validated across 14 races with variance analysis
- Cross-race generalization: Models trained on one race predict others with MAE < 2.5 positions

**User Experience:**
- Race Insights: Instant load (precomputed parquet)
- Race Analytics: 1-2 min telemetry load, then real-time lap-by-lap simulation
- Model Validation: Cross-race performance metrics across all 14 datasets

---

## What's Next

**Immediate:**
- Create demo video showing real-time coaching in action
- Add driver comparison view (select 2 drivers, compare profiles side-by-side)
- Enhance local performance with caching optimizations

**Future Vision:**
- Real-time data ingestion from live races
- Mobile-responsive design for pit lane use
- Expand beyond GR Cup to other race series
- Automated report generation (PDF export of Race Insights)
- Driver progress tracking across season

---

## Why This Matters

Traditional motorsport analytics focuses on **what happened**. Predictive analytics tells you **what will happen**.

RaceIQ does something different: it answers **"what should I do differently?"**

It's the difference between:
- "You were 18.3 seconds behind the leader" → **vs** → "You lost 15.4s to P9 through late-stint tire degradation"
- "Your lap times were inconsistent" → **vs** → "Traffic on laps 7, 12, and 15 cost you 4.2 seconds total"
- "You should improve your technique" → **vs** → "Matching top-5 degradation would gain you 2 positions"

**Data-driven coaching means quantified, specific, actionable insights.** That's what RaceIQ delivers.

---

## Try It Yourself

```bash
# Clone and setup
git clone https://github.com/yourusername/RaceIQ
cd RaceIQ
uv venv && source .venv/bin/activate
uv pip install -e .

# Run the dashboard
streamlit run Dashboard.py
```

Select a track and race, explore the three analysis modes:
1. **Race Analytics** - Simulate lap-by-lap with live coaching
2. **Race Insights** - Beat-the-ahead analysis + counterfactual scenarios
3. **Model Validation** - See prediction accuracy across all 14 races

---

*Built for the Toyota Gazoo Racing Hack the Track 2025 hackathon.*
*Category: Real-Time Analytics*
*Team: [Your Name]*
