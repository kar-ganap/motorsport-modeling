# Demo Script Recommendations - Quick Reference

## Selected (Track, Race, Driver) Triplets

### Race Analytics Page
- **Primary:** Indianapolis Race 2, Driver #89 (P8)
  - Narrative length: 657 chars (detailed analysis)
  - Mid-pack position (good for showing competitive racing)
  - Full telemetry suite available (247K samples)

- **Alternative:** Barber Race 2, Driver #55 (P2)
  - Longest narrative: 738 chars
  - Top finisher (shows winning performance)
  - Different track characteristics

### Race Insights Page
- **Primary:** Sebring Race 2, Driver #51 (P9)
  - Smallest gap: only 0.10s behind P8
  - Pace delta: +0.007s/lap (incredibly close battle)
  - Perfect example of "beat-the-driver-ahead" analysis

- **Alternative:** Sebring Race 1, Driver #63 (P6)
  - Gap: 0.18s behind P5
  - Focus: tire degradation as primary differentiator
  - Good narrative explaining performance delta

### Model Validation Page
- **Sebring Race 1 - Clearest Monotonic Trends (MAE: ~1.2s for warmup=5, horizon=1)**
- Focus on MAE contour plot showing:
  - Monotonic improvement with more warm-up laps (left-to-right)
  - Monotonic worsening with longer prediction horizons (bottom-to-top)
  - Per-race breakdown table comparing all 14 races

---

## Data Analysis Findings

### Closest Mid-Pack Battles (All Races)
1. Sebring Race 2, Driver #32 (P9): **0.10s gap**
2. Sebring Race 1, Driver #63 (P6): 0.18s gap
3. Road America Race 2, Driver #15 (P8): 0.18s gap
4. Road America Race 2, Driver #16 (P5): 0.19s gap
5. Barber Race 1, Driver #98 (P7): 0.20s gap

### Most Detailed Narratives
1. Barber Race 2, Driver #55 (P2): 738 chars
2. Sonoma Race 1, Driver #13 (P9): 728 chars
3. COTA Race 1, Driver #4 (P5): 704 chars
4. Barber Race 1, Driver #78 (P13): 680 chars
5. Indianapolis Race 2, Driver #89 (P8): 657 chars

### Tightest Championship Battles (P1 vs P2)
1. VIR Race 1: Winner vs P2 = **0.10s**
2. VIR Race 2: Winner vs P2 = 0.10s
3. Sonoma Race 2: Winner vs P2 = 0.41s
4. Road America Race 1: Winner vs P2 = 0.43s
5. Road America Race 2: Winner vs P2 = 1.85s

---

## Narrative Flow

### The Story Arc
1. **Real-time** (Race Analytics) → "During the race, coaching in real-time"
2. **Post-race** (Race Insights) → "After the race, analyzing what separated drivers"
3. **Validation** (Model Validation) → "Proving these insights are accurate"

### Transition Scripts
- **Analytics → Insights:**
  > "We've seen real-time coaching during the race. Now let's analyze what separated drivers in the final results - answering: what would it take to beat the driver directly ahead?"

- **Insights → Validation:**
  > "These insights rely on predictive models. Let's validate their accuracy across all 14 races to ensure our recommendations are trustworthy."

---

## Key Demo Talking Points

### For Race Analytics
- "247,000 telemetry samples per race"
- "Sub-second prediction updates during live racing"
- "NOW section shows ACTUAL data: position, gaps, last lap time"
- "NEXT forecast: ALL BARS PURPLE - negative = faster (threat), positive = slower (opportunity)"
- "Gap Analysis: RED = ahead, GREEN = behind - ACTUAL measured gaps"
- "Sector Performance: GREEN = faster, RED = slower - based on LAST COMPLETED LAP"
- "Gold stars = battles when gap < 1.0 second"

### For Race Insights
- "Beat-the-driver-ahead: comparing to the specific person directly ahead"
- "AI-generated narratives quantify the exact performance differences"
- "Separates controllable vs. uncontrollable factors"
- "Counterfactual scenarios show improvement potential"

### For Model Validation
- "Using Sebring Race 1 - clearest monotonic trends across both dimensions"
- "14 races analyzed across 7 different tracks"
- "Warm-up laps improve prediction accuracy (left-to-right on contour)"
- "Longer horizons increase uncertainty (bottom-to-top on contour)"
- "Sweet spot: 3-5 warm-up laps for next-lap, achieving MAE ~1.2s for Sebring Race 1"

---

## Technical Checklist

### Before Demo
- [ ] Start Dashboard.py: `streamlit run Dashboard.py`
- [ ] Pre-load Race Analytics page (Indianapolis Race 2, Driver #89)
- [ ] Pre-load Race Insights page (Sebring Race 2, Driver #51)
- [ ] Check Model Validation page loads correctly
- [ ] Browser zoom set to 100-110%
- [ ] Have backup examples ready (Barber, Sebring Race 1)

### During Demo
- [ ] Navigate using sidebar (consistent UI)
- [ ] Point to specific lap numbers when discussing trends
- [ ] Highlight specific telemetry features (throttle smoothness, brake points)
- [ ] Read short excerpts from AI narratives (not full text)
- [ ] Show MAE contour plot patterns clearly

### Backup Plans
- If Indianapolis loads slowly → Use Barber Race 2 instead
- If telemetry plots lag → Focus on coaching insights text
- If Race Insights errors → Use comparative metrics table only
- If counterfactuals missing → Skip that section, focus on beat-ahead

---

## Timing Budget

| Section | Target Time |
|---------|-------------|
| Introduction | 10s |
| Race Analytics | 90-120s |
| Transition 1 | 10s |
| Race Insights | 90-120s |
| Transition 2 | 10s |
| Model Validation | 60-90s |
| Closing | 10s |
| **TOTAL** | **280-370s (4:40-6:10)** |

**Target:** 3:00-4:30 → Cut optional sections, speed up if over time

---

## Questions to Anticipate

**Q: How do you handle different tracks?**
A: "We've validated across 7 different tracks (Indy, Sebring, COTA, VIR, Barber, Road America, Sonoma) - model performs consistently"

**Q: How real-time is this?**
A: "Predictions update every lap with sub-second computation time - fast enough for live race engineering decisions"

**Q: What data do you need?**
A: "Four core telemetry channels (speed, throttle, brake, accelerometer) sampled at ~10Hz plus lap times - standard GR Cup data"

**Q: Can this work for other series?**
A: "Yes - the methodology is track and series agnostic. We'd need to retrain on new data, but the approach transfers"

**Q: How accurate are the predictions?**
A: "Mean absolute error of ~2 seconds for next-lap predictions with 3-5 warm-up laps - shown on Model Validation page"
