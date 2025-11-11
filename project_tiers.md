# Project Tiers: Baseline → Good → Ambitious

## Philosophy

Each tier is a **complete, submittable project**. You're not building "half a project" at baseline - you're building a focused, polished tool that does ONE thing well, then expanding from there.

---

## 🥉 BASELINE TIER: "Driver Performance Analyzer"

### Tagline
"Data-driven driver coaching for GR Cup racing"

### Core Deliverable
**Static analysis dashboard** showing technique quality for all Indianapolis Race 1 drivers, with improvement recommendations.

### What You Build

**1. Data Loading & Cleaning**
```python
# Load Indianapolis R1 telemetry (21.4M rows)
# Calculate 10 high-confidence metrics for all 19 drivers
# Rank drivers by technique quality
```

**2. Technique Metrics Module**
Implement these 5 metrics (from the 10):
- Consistency (σ of lap times)
- Coasting time percentage
- Braking smoothness (pulse count)
- Throttle timing (apex → full throttle)
- Combined G-force usage

**3. Static Dashboard**
Single-page web app (Streamlit) showing:
- Leaderboard: Drivers ranked by technique score
- Driver cards: Individual metrics for each driver
- Comparison: Winner vs. runner-up metrics side-by-side
- Recommendations: "Improve braking smoothness → gain 0.4s/lap"

### Demo Flow (3 minutes)

**Minute 1:** Problem statement
- "GR Cup teams need data to improve driver performance"
- "We analyzed 19 drivers at Indianapolis to find who has best technique"

**Minute 2:** Dashboard walkthrough
- "Here's the leaderboard - #55 Kohlbecker has best technique score"
- "He excels at braking smoothness and throttle discipline"
- "Runner-up #2 Robusto is close, but has higher coasting time"
- "Our system recommends: reduce coasting → gain 0.3s/lap"

**Minute 3:** Impact
- "Teams can use this to identify training priorities"
- "Data-backed coaching instead of gut feel"
- "Works on any track with telemetry data"

### Effort Estimate
- **Week 1:** Data loading, metric calculations, validation
- **Week 2:** Dashboard UI, polish
- **Week 3:** Documentation, video, presentation prep

### Strengths
✅ Technically solid (defensible metrics)
✅ Practical value (teams can actually use it)
✅ Achievable (no GPS complexity)
✅ Complete story (problem → solution → impact)

### Weaknesses
❌ No predictions (just analysis)
❌ No GPS visuals (less "wow")
❌ Static only (not "real-time")
❌ Category 1 focus (not Category 4)

### Submission Details
- **Category:** Driver Training & Insights (Category 1)
- **Dataset:** Indianapolis R1 only
- **Published Project:** Streamlit app on free hosting
- **Code Repo:** Clean Python package with docs

---

## 🥈 GOOD TIER: "RaceCraft Insights - Predictive Driver Coach"

### Tagline
"Real-time race analytics with predictive coaching"

### Core Deliverable
**Lap-by-lap analysis tool** that predicts performance degradation and provides coaching recommendations.

### What You Build (Baseline + )

**Everything from Baseline, PLUS:**

**4. Predictive Models**
```python
# Tire degradation model
# Input: Laps 1-10 data
# Output: Predicted lap times for laps 11-26
# Accuracy target: RMSE < 0.5s

# Technique degradation detector
# Input: Current lap metrics
# Output: Alert if technique degrading vs. baseline
```

**5. Lap-by-Lap Timeline**
Interactive timeline showing:
- Actual lap times vs. predicted
- Technique alerts ("Lap 12: Braking degrading")
- Gap evolution (P1 vs P2 gap over time)

**6. Sector Analysis**
- Break down lap time into S1/S2/S3
- Show which sector driver is weak
- Predict sector times for future laps

### Demo Flow (3 minutes)

**Minute 1:** Problem + Innovation
- "Race engineers need to predict performance and catch issues early"
- "We built a system that predicts lap-by-lap degradation"

**Minute 2:** Live Analysis
- "Let's analyze Indianapolis Race 1 lap-by-lap"
- *[Show timeline with predictions]*
- "Lap 5: System predicts lap 15 will be 1:41.2 → Actual: 1:41.0 ✓"
- "Lap 12: Alert! Driver #2 braking quality dropping"
- *[Show technique metrics degrading]*
- "Recommendation: Focus on Turn 5 brake release"

**Minute 3:** Outcome
- "System predicted final gap: 0.2s → Actual: 0.17s (15% error)"
- "Identified correctable issues that cost #2 the win"
- "Teams can use this during races for real-time decisions"

### Effort Estimate
- **Week 1:** Baseline features + predictive models
- **Week 2:** Timeline UI, sector analysis
- **Week 3:** Polish, validation, video

### Strengths
✅ Predictive element (your key desire)
✅ Tells a better story (prediction → validation)
✅ More engaging demo (lap-by-lap progression)
✅ Still achievable (no GPS required)
✅ Category 4 compliant (real-time analytics)

### Weaknesses
❌ Still no GPS (missing visual wow)
❌ Predictions only validated on historical data
❌ Can't simulate "what-if" scenarios

### Submission Details
- **Category:** Real-Time Analytics (Category 4)
- **Dataset:** Indianapolis R1 + R2 (for validation)
- **Published Project:** Interactive Streamlit dashboard
- **Code Repo:** Includes trained models + notebooks

---

## 🥇 AMBITIOUS TIER: "RaceCraft AI - Digital Race Engineer"

### Tagline
"AI-powered race engineering with GPS-validated insights"

### Core Deliverable
**Full real-time simulation system** with GPS visualization, predictions, coaching, and strategy optimization.

### What You Build (Good + )

**Everything from Good, PLUS:**

**7. GPS Racing Line Analysis**
```python
# Extract 4.47M GPS coordinates
# Identify corners from GPS clustering
# Visualize racing lines (winner vs runner-up)
# Color-code by speed, throttle, braking
```

**8. Strategy Optimizer**
```python
# Pit window calculator
# Input: Current lap, tire deg rate, gaps
# Output: Optimal pit lap (minimize position loss)

# What-if simulator
# "If driver pits on lap 15 vs lap 18, what's final position?"
```

**9. Interactive Race Replay**
- Animated replay of race
- Cars moving on GPS track map
- Live predictions updating lap-by-lap
- Real-time coaching alerts popping up
- Position changes visualized

**10. Multi-Race Learning**
- Train on Race 1, validate on Race 2
- "Did drivers improve based on our recommendations?"
- Cross-race technique consistency analysis

### Demo Flow (3 minutes)

**Minute 1:** Setup the story
- "0.17 seconds separated winner from runner-up at Indianapolis"
- "Could the runner-up have won with better coaching?"
- "We built an AI race engineer to find out"

**Minute 2:** Live Replay (the wow moment)
- *[Animated GPS map showing both cars racing]*
- "Lap 7: Both drivers on identical pace"
- *[Zoom to Turn 5 GPS comparison]*
- "Winner takes wider line → 6 km/h faster exit"
- *[Show technique alert]*
- "Lap 12: System detects #2's braking degrading"
- *[Show recommendation popup]*
- "Recommendation: Brake smoother → gain 0.4s/lap"
- *[Fast forward to finish]*
- "Final gap: 0.17s - exactly what we predicted"

**Minute 3:** The reveal
- "If #2 had followed our coaching on lap 12..."
- *[Show corrected simulation]*
- "Estimated outcome: #2 wins by 0.05s"
- "This isn't just analysis - it's actionable race intelligence"
- "Teams can use this live during races"

### Effort Estimate
- **Week 1:** Baseline + predictive models (tight schedule!)
- **Week 2:** GPS extraction, visualization, corner ID (full sprint)
- **Week 3:** Animation, strategy optimizer, final polish (crunch time)

### Strengths
✅ Everything you wanted (predictions + coaching + wow)
✅ GPS visual wow factor
✅ Complete Category 4 implementation
✅ Multiple data sources used (telemetry + GPS + timing + results)
✅ Compelling narrative with visual proof
✅ Could actually win the hackathon

### Risks
⚠️ Aggressive timeline (might not finish everything)
⚠️ GPS parsing could have unexpected issues
⚠️ Animation might be buggy
⚠️ Scope creep risk (trying to do too much)

### Mitigation Strategy
- **Week 1 checkpoint:** Must have baseline tier working
- **Week 2 checkpoint:** Must have predictions + basic GPS
- **Week 3 focus:** Polish what exists, don't add new features
- **Backup plan:** Cut animation if needed (use static GPS viz)

### Submission Details
- **Category:** Real-Time Analytics (Category 4)
- **Dataset:** Indianapolis R1 + R2 (full dataset)
- **Published Project:** Full-featured web app (might need paid hosting)
- **Code Repo:** Production-quality code with ML pipeline

---

## Tier Comparison Matrix

| Feature | Baseline | Good | Ambitious |
|---------|----------|------|-----------|
| **Time commitment** | 2 weeks | 2.5 weeks | 3+ weeks |
| **Risk level** | Low | Medium | High |
| **Technical depth** | Medium | High | Very High |
| **Wow factor** | Low | Medium | High |
| **Win probability** | 20% | 50% | 70% |
| | | | |
| **Data sources** | Telemetry only | Telemetry + Timing | All sources + GPS |
| **Technique metrics** | 5 metrics | 10 metrics | 10 metrics + GPS |
| **Predictions** | ❌ None | ✅ Lap times | ✅ Lap times + Position + Strategy |
| **GPS visualization** | ❌ None | ❌ None | ✅ Racing lines + Speed maps |
| **Real-time simulation** | ❌ Static only | ⚠️ Lap-by-lap | ✅ Full replay |
| **Strategy optimizer** | ❌ None | ❌ None | ✅ Pit window + What-if |
| **Category fit** | Category 1 | Category 4 | Category 4++ |
| | | | |
| **Demo quality** | PowerPoint + static dash | Interactive timeline | Live animated replay |
| **Story strength** | "Here's what we found" | "Here's what we predicted" | "Here's how #2 could have won" |

---

## Recommended Path: **"Good Tier with Ambitious Stretch Goals"**

### Strategy
Start with Good Tier as your **target**, with Ambitious features as **stretch goals**.

### Week-by-Week Plan

**Week 1: Lock in Good Tier Foundation**
- Days 1-2: Data loading + 5 core metrics (baseline requirement)
- Days 3-4: Remaining 5 metrics + dashboard (baseline complete ✓)
- Days 5-7: Predictive models (good tier requirement)

**End of Week 1 Checkpoint:**
- ✅ Have working baseline tier
- ✅ On track for good tier
- ⚠️ Decide: Go for ambitious or consolidate?

**Week 2: Push for Ambitious (Conditionally)**

**If Week 1 went well:**
- Days 8-10: GPS extraction + corner identification
- Days 11-12: Racing line visualization
- Days 13-14: Timeline UI + sector analysis

**If Week 1 was challenging:**
- Days 8-10: Polish predictive models
- Days 11-12: Improve dashboard UI
- Days 13-14: Add Race 2 validation

**End of Week 2 Checkpoint:**
- ✅ Must have working good tier
- ⚠️ Ambitious tier: 0%, 50%, or 100%?

**Week 3: Polish & Finish**

**If you have ambitious tier working:**
- Days 15-16: Animation OR strategy optimizer (pick one!)
- Days 17-18: Bug fixes, polish
- Days 19-21: Video, documentation, presentation

**If you only have good tier:**
- Days 15-16: Add impressive visualizations (plots, charts)
- Days 17-18: Make predictions really accurate
- Days 19-21: Killer video showing predictions working

---

## Decision Framework

### Choose BASELINE if:
- ⏰ You have < 2 weeks
- 🎯 You prioritize "done well" over "feature-rich"
- 📊 You're more comfortable with analysis than ML
- ✅ You want guaranteed completion

### Choose GOOD if:
- ⏰ You have 2-3 weeks
- 🎯 You want predictions (your stated goal)
- 📊 You're comfortable with Python + ML basics
- ✅ You want Category 4 compliance

### Choose AMBITIOUS if:
- ⏰ You have 3+ weeks dedicated time
- 🎯 You want to maximize win probability
- 📊 You're comfortable with GPS parsing + visualization
- ✅ You're willing to risk scope creep
- 🏆 You want that "wow" moment

---

## My Recommendation

**Target: Good Tier**
**Stretch: Ambitious GPS features**
**Fallback: Baseline tier (if Week 1 goes poorly)**

### Why This Works

1. **Week 1 = Baseline tier** (guaranteed submission)
2. **Week 2 = Good tier** (strong submission with predictions)
3. **Week 3 = Ambitious features OR polish** (adaptive based on progress)

### The Pitch Adjusts Based on What You Finish

**If you finish Baseline:**
"We analyzed 19 GR Cup drivers using 5 key technique metrics and identified specific, measurable improvements for each driver."

**If you finish Good:**
"We built a predictive race analytics system that forecasts lap-by-lap performance degradation and provides real-time coaching recommendations."

**If you finish Ambitious:**
"We created an AI race engineer that combines GPS racing line analysis, predictive modeling, and strategy optimization to show exactly how the runner-up could have won Indianapolis by 0.05 seconds."

### All three are valid submissions. The question is: which story do you want to tell?

---

## Week 1 Deliverable (Gates All Tiers)

No matter which tier you target, Week 1 MUST deliver:

```python
# Data loading works
indy_data = load_indianapolis_race1()  # 21.4M rows loaded ✓

# Basic metrics calculated
for driver in drivers:
    metrics = {
        'consistency': calculate_consistency(driver),
        'coasting': calculate_coasting(driver),
        'braking': calculate_braking(driver),
        'throttle': calculate_throttle(driver),
        'g_force': calculate_g_force(driver)
    }
    driver.baseline_metrics = metrics

# Rankings work
leaderboard = rank_drivers(drivers)
print(leaderboard)
# Output:
# 1. Driver #55: Score 9.2/10
# 2. Driver #2:  Score 8.8/10
# ...
```

**If this doesn't work by end of Week 1, you're in trouble for any tier.**

---

## The Safety Net

Remember: Even baseline tier is a **strong hackathon project** if executed well.

5 solid metrics + clear rankings + actionable recommendations = practical tool that teams can use.

Don't feel like you "failed" if you only hit baseline. A polished baseline beats a buggy ambitious every time.

**Judge's perspective:**
- Baseline (polished): "This is solid, useful work"
- Good (working): "This is impressive, shows ML skills"
- Ambitious (working): "This could win"
- Ambitious (broken): "They bit off too much"

**Risk-adjusted value:**
- Baseline: 8/10 project, 95% completion chance = 7.6 expected value
- Good: 9/10 project, 75% completion chance = 6.75 expected value
- Ambitious: 10/10 project, 50% completion chance = 5.0 expected value

**Choose your risk tolerance accordingly.**

What tier are you leaning toward?
