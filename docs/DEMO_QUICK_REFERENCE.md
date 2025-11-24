# RaceIQ Demo - Quick Reference Card

**Target:** 3:00-4:30 total | **Track:** Keep it tight, cut optional sections if over time

---

## Selected Examples

| Page | Race | Driver | Why |
|------|------|--------|-----|
| **Race Analytics** | Indianapolis R2 | #89 (P8) | Mid-pack, shows all 5 sections |
| **Race Insights** | Sebring R2 | #51 (P9) | **0.10s gap!** Closest battle |
| **Model Validation** | Sebring R1 | Aggregate | Clearest trends (warmup↑=MAE↓, horizon↑=MAE↑) |

---

## Part 1: Race Analytics (115s)

### CRITICAL Architecture Point
> "Profile from laps 1-5, coaching starts lap 6"

### 5 Sections (in order)
1. **NOW** - Current state cards (P8, gaps, lap time) - ALL ACTUAL DATA
2. **NEXT** - Forecast bar chart (YOU vs ±3, time deltas) - PREDICTED
3. **RACE CONTEXT** - 3 plots (ALL ACTUAL DATA):
   - **Gap Analysis (top):** RED = ahead, GREEN = behind, measured gaps in seconds
   - **Sector Performance (middle):** GREEN = faster, RED = slower, last completed lap
   - **Position Progression (bottom):** Blue line = you, stars = battles (gap < 1s)
4. **DIAGNOSTICS** - ⚠️ Conditional technique alerts
5. **RADIO** - Coaching message ("P8 | Strong pace | Focus S2")

### Demo Flow
- Start lap 6 → advance to 10 → advance to 13-15
- Point to NEXT forecast: **"ALL BARS PURPLE. Negative = they're FASTER (threat), Positive = they're SLOWER (opportunity)"**
- Show 3 RACE CONTEXT plots in sequence: Gap Analysis (top), Sector Performance (middle), Position Progression (bottom)
- If DIAGNOSTICS appear: "Only shows when deviating from baseline"
- End with RADIO message

---

## Part 2: Race Insights (90-110s)

### Key Concept
> "Beat-the-driver-ahead: compare to specific person ahead, not generic field"

### The Story
- Sebring R2, Driver #51 (P9) vs P8
- **Only 0.10s separated them!**
- AI narrative quantifies primary factor
- Separates controllable vs uncontrollable

### Demo Flow
1. Select Sebring R2, Driver #51
2. Show comparative metrics (pace, deg, traffic, sectors)
3. Read excerpt from AI narrative (30s)
4. **[OPTIONAL]** Show counterfactual what-if (cut if over time)
5. Close with "Data-driven priorities for next race"

---

## Part 3: Model Validation (75s)

### Sebring Race 1 - Clearest Trends
> "Shows clearest monotonic trends across both dimensions"

### MAE Contour Plot - Two Trends
**Left → Right:** More warm-up laps = **BETTER** (monotonic improvement)
**Bottom → Top:** Longer horizon = **WORSE** (monotonic degradation)

### Sweet Spot
> "3-5 laps for next-lap prediction = MAE ~1.2s for Sebring Race 1, <2s average"

### Demo Flow
1. Point to X-axis (warm-up laps): "More data = better predictions"
2. Point to Y-axis (prediction horizon): "Further ahead = harder to predict"
3. Show color scale (MAE in seconds): "~1.2s for Sebring Race 1"
4. Quick scroll through per-race metrics table
5. Close: "Real-time → post-race → validated"

---

## Must-Mention Points

✅ **Race Analytics**
- [ ] "Laps 1-5 baseline, lap 6 start coaching"
- [ ] "5 sections: NOW, NEXT, CONTEXT, DIAGNOSTICS, RADIO"
- [ ] "NOW = ACTUAL data (position, gaps, last lap)"
- [ ] "NEXT = PREDICTED: ALL BARS PURPLE, negative = faster (threat)"
- [ ] "RACE CONTEXT = 3 plots: Gap Analysis (top), Sector Performance (middle), Position Progression (bottom)"
- [ ] "Gap Analysis: RED ahead, GREEN behind - ACTUAL gaps"
- [ ] "Sector Performance: GREEN faster, RED slower - LAST LAP"
- [ ] "Gold stars = battles (gap < 1.0s)"
- [ ] "DIAGNOSTICS only when technique deviates"

✅ **Race Insights**
- [ ] "Only 0.10s gap - incredibly close"
- [ ] "Beat specific driver ahead, not field average"
- [ ] "AI quantifies primary factor"

✅ **Model Validation**
- [ ] "Sebring Race 1 - clearest monotonic trends"
- [ ] "Two monotonic trends in MAE contour"
- [ ] "More laps = better, longer horizon = worse"
- [ ] "MAE ~1.2s for Sebring Race 1"

---

## Time Management

| Section | Time | Cut if Over |
|---------|------|-------------|
| Analytics | 115s | Skip lap 6, go straight to 10 |
| Insights | 90-110s | Cut counterfactual what-if |
| Validation | 75s | Skip per-race table |

**Running Total Check:** After Race Analytics, should be ~2:00. After Race Insights, ~3:30.

---

## Backup Plans

| Problem | Fix |
|---------|-----|
| No DIAGNOSTICS showing | "None detected - system only shows when needed" |
| Counterfactuals missing | Skip entirely |
| MAE plot unclear | Focus on table instead |
| Running over time | Cut all optional sections, speed up scrolling |

---

## Q&A Cheat Sheet

**Q:** How real-time?
**A:** "Lap-by-lap, sub-second computation"

**Q:** Different tracks?
**A:** "7 tracks validated, model is track-agnostic"

**Q:** Why laps 1-5?
**A:** "Enough data for robust baseline, before conditions change"

**Q:** Required data?
**A:** "Lap times required, telemetry optional for deeper analysis"

**Q:** Why negative in forecast?
**A:** "Negative = they're predicted FASTER (lower time). Positive = SLOWER (higher time)"

**Q:** Are gaps predicted or actual?
**A:** "Gap Analysis shows ACTUAL measured gaps. NEXT forecast shows PREDICTED lap times"

---

## Opening & Closing Lines

**OPEN:**
> "RaceIQ is an AI-powered racing intelligence platform for Toyota Gazoo Racing. It provides three core capabilities: real-time coaching during races, post-race performance analysis, and validated predictive models. Let me show you how it works."

**CLOSE:**
> "From real-time coaching during the race, to post-race analysis of what separated drivers, to validated predictions proving it works - RaceIQ transforms telemetry into racing intelligence."

---

## Page Navigation

```
Dashboard.py → Race Analytics (in sidebar)
→ Navigate to Race Insights
→ Navigate to Model Validation
```

**Pre-load:** Indy R2, Driver #89 ready to go at lap 6

---

## Color Coding Reference (Critical!)

### Field Forecast (NEXT section)
- **ALL BARS: Purple (#667eea)**
- Negative value = driver FASTER than you (threat)
- Positive value = driver SLOWER than you (opportunity)

### Gap Analysis
- **RED (#dc2626):** Gap to car AHEAD
- **GREEN (#16a34a):** Gap to car BEHIND

### Sector Performance
- **GREEN (#10b981):** You were FASTER than field
- **RED (#f43f5e):** You were SLOWER than field

### Battles (Gold Stars)
- **GOLD/AMBER (#f59e0b):** When gap < 1.0 second
