# RaceIQ Demo Script (3-4.5 minutes)

**Created:** November 2025
**Target Time:** 3:00 - 4:30

---

## Demo Setup

**Selected Examples:**
- **Race Analytics:** Indianapolis Race 2, Driver #89 (P8)
- **Race Insights:** Sebring Race 2, Driver #51 (P9) - 0.10s gap to P8
- **Model Validation:** Sebring Race 1 (clearest monotonic trends: warmup↑ = MAE↓, horizon↑ = MAE↑)

**Pre-Demo Checklist:**
- [ ] Dashboard running: `streamlit run Dashboard.py`
- [ ] Browser at 100% zoom
- [ ] Pre-load Race Analytics page (Indianapolis Race 2, Driver #89)
- [ ] Have Sebring Race 2 ready for Race Insights

---

## Part 1: Race Analytics - Real-Time Coaching (90-120s)

### Opening (15s)
> "RaceIQ is an AI-powered racing intelligence platform for Toyota Gazoo Racing. It provides three core capabilities: real-time coaching during races, post-race performance analysis, and validated predictive models. Let me show you how it works."

**Action:** Show Indianapolis Race 2, Driver #89 selected, lap slider at 6

### System Architecture (10s)
> "This is critical: we build a driver profile from laps 1-5 to understand their normal driving characteristics. Coaching simulation begins at lap 6, comparing real-time performance against that baseline."

### Section 1: NOW - Current State (10s)
> "At a glance: current position P8, gap ahead, gap behind, and last lap time. These are all ACTUAL data from completed laps - not predictions. The large metric cards update as we advance through the race."

**Action:** Advance slider to lap 10

### Section 2: NEXT LAP FORECAST (20s)
> "This horizontal bar chart shows PREDICTED next lap time versus nearby drivers. The Y-axis shows relative positions: -3, -2, -1, YOU, +1, +2, +3."

> "Bars show time delta in seconds - ALL BARS ARE PURPLE. Crucially: negative bars mean that driver is predicted FASTER than you - that's a threat. Positive bars mean they're predicted SLOWER - that's an opportunity to attack."

**Action:** Point to specific bars, emphasize negative = faster (bad), positive = slower (good)

### Section 3: RACE CONTEXT - Three Plots (35s)
> "Three integrated views of actual race dynamics, all based on historical data:"

**Gap Analysis (top):**
> "Real-time gaps to cars ahead and behind. RED line shows gap to car ahead, GREEN line shows gap to car behind. These are ACTUAL measured gaps in seconds, not predictions. Critical for knowing when to push or defend."

**Sector Performance (middle):**
> "Three-sector breakdown of your LAST COMPLETED LAP versus field median. GREEN sectors mean you were faster than the field, RED sectors mean slower. This tells you WHERE on track you're losing or gaining time."

**Position Progression (bottom):**
> "Your driver in bold blue, field in gray. Gold stars mark wheel-to-wheel battles - these appear when gap between cars is under 1 second. You can see position changes lap-by-lap."

**Action:** Advance to lap 13-15 to show progression

### Section 4: DIAGNOSTICS (Conditional) (15s)
> "When the system detects technique deviations from the lap 1-5 baseline, it flags specific issues:"

> "Example: 'Excessive mid-corner lift-offs - costing 0.3s per lap' or 'Inconsistent braking points in Turn 6'"

> "These only appear when there's a problem detected - it's not always shown. If nothing appears, the driver is performing within their normal baseline."

**Action:** If visible, highlight diagnostic message; if not, explain it's conditional

### Section 5: RADIO MESSAGE (10s)
> "Finally, the actionable coaching message in race-engineer language:"

> "Example: 'P8 | Strong pace - push to gain positions | Focus S2 (losing 0.4s)'"

> "This is what goes over the radio - concise, actionable, prioritized."

---

## Part 2: Race Insights - Post-Race Analysis (90-120s)

### Transition (10s)
> "That's real-time coaching during the race. Now let's analyze what separated drivers in the final results."

**Action:** Navigate to Race Insights page, select Sebring Race 2

### Beat-the-Driver-Ahead Concept (15s)
> "This isn't generic analysis - we compare each driver to the specific person directly ahead in the results. For our Driver #51 in P9, we analyze what it would take to beat P8."

> "This was an incredibly close race - only 0.10 seconds separated them over the entire event."

**Action:** Select Driver #51 (P9)

### Comparative Metrics (30s)
> "We break down the performance delta into quantifiable factors:"

- **Pace Analysis:** "Early stint, mid-race, late-race pace comparison"
- **Tire Degradation:** "Degradation rate: ours vs theirs vs field average"
- **Traffic Impact:** "Laps spent in traffic, estimated time cost"
- **Sector Performance:** "Which sectors cost us the position"

**Action:** Scroll through comparative metrics section

### AI-Generated Narrative (25s)
> "GPT analyzes all these metrics and generates a detailed narrative explaining the primary factor:"

**Read excerpt from narrative (example):**
> "The primary factor was slower early-stint pace, losing 1.13 seconds per lap in laps 6-10. Despite matching pace mid-race and slightly better tire degradation late, we couldn't recover the early deficit..."

> "Notice it quantifies everything and separates controllable factors (our pace) from uncontrollable ones (their tire strategy)."

### What-If Scenarios (Optional, 20s if time permits)
> "Counterfactual analysis: what if we matched field-average consistency? The model predicts we'd gain 2 positions and save 3.4 seconds."

> "This helps teams prioritize: is it worth focusing on consistency training, or tire management, or sector-specific technique?"

**Action:** Show counterfactual predictions if available

### Closing Insight Message (10s)
> "All of this gets synthesized into coaching priorities for the next race - data-driven, specific, actionable."

---

## Part 3: Model Validation - Prediction Accuracy (60-90s)

### Transition (10s)
> "These insights rely on predictive models. Let's validate their accuracy using our best-performing race to prove they're trustworthy."

**Action:** Navigate to Model Validation page

### MAE Contour Plot (40s)
> "This contour plot shows prediction accuracy for Sebring Race 1, which shows the clearest monotonic trends across all 14 races. Two dimensions:"

**X-axis (Warm-up Laps):**
> "How many laps we use to build the driver profile. Notice error DECREASES left-to-right - more data improves predictions. That's why we use laps 1-5."

**Y-axis (Prediction Horizon):**
> "How many laps into the future we're predicting. Error INCREASES bottom-to-top - harder to predict further ahead. This is expected behavior."

**Color (MAE):**
> "Mean absolute error in seconds. Dark blue/purple is better - lower error."

> "Sweet spot: 3-5 warm-up laps for next-lap predictions gives us MAE of 1.2 seconds for Sebring Race 1. That's excellent for actionable coaching."

**Action:** Point to different regions of contour plot

### Performance Metrics (20s)
> "Aggregate statistics across all 14 races:"
- MAE ranges from 0.6s (lowest: Barber) to 3.5s (Sonoma Race 1)
- Most races achieve MAE under 2s for next-lap predictions
- R² scores showing model fit
- Position prediction accuracy for top-5 finishes

> "Consistent performance across different tracks validates model robustness."

**Action:** Quick scroll through per-race breakdown table

### Closing (5s)
> "From real-time coaching to post-race analysis to validated predictions - RaceIQ transforms telemetry into racing intelligence."

---

## Timing Breakdown

| Section | Target Time |
|---------|-------------|
| **Race Analytics** | |
| Opening & Architecture | 25s |
| NOW + NEXT | 30s |
| RACE CONTEXT (3 plots) | 35s |
| DIAGNOSTICS + RADIO | 25s |
| **Subtotal** | **115s** |
| | |
| **Race Insights** | |
| Transition + Concept | 25s |
| Comparative Metrics | 30s |
| AI Narrative | 25s |
| What-If (optional) | 20s |
| Closing | 10s |
| **Subtotal** | **90-110s** |
| | |
| **Model Validation** | |
| Transition | 10s |
| MAE Contour | 40s |
| Metrics | 20s |
| Closing | 5s |
| **Subtotal** | **75s** |
| | |
| **TOTAL** | **280-300s (4:40-5:00)** |

**To hit 3:00-4:30:** Cut what-if scenarios, speed up metric scrolling, condense narrative reading

---

## Key Talking Points (Must Mention)

### Race Analytics
- ✅ "Driver profile from laps 1-5, coaching starts lap 6"
- ✅ "5 sections: NOW, NEXT, RACE CONTEXT, DIAGNOSTICS (conditional), RADIO"
- ✅ "NOW shows ACTUAL data: position, gaps, last lap time"
- ✅ "NEXT forecast: negative = they're faster (threat), positive = they're slower (opportunity)"
- ✅ "All forecast bars are PURPLE - no red/green conditional coloring"
- ✅ "RACE CONTEXT has 3 plots: Gap Analysis (top), Sector Performance (middle), Position Progression (bottom)"
- ✅ "Gap Analysis: RED = ahead, GREEN = behind, shows ACTUAL historical gaps"
- ✅ "Sector Performance: GREEN = faster, RED = slower, based on LAST COMPLETED LAP"
- ✅ "Gold stars = battles when gap < 1 second"
- ✅ "DIAGNOSTICS only appear when technique deviates from baseline"

### Race Insights
- ✅ "Beat-the-driver-ahead: compare to specific person ahead, not generic field"
- ✅ "Only 0.10s separated P8 and P9 in Sebring - incredibly close"
- ✅ "AI narrative quantifies primary factor with specific numbers"
- ✅ "Separates controllable vs uncontrollable factors"

### Model Validation
- ✅ "Using Sebring Race 1 - clearest demonstration of both monotonic trends"
- ✅ "MAE contour shows two monotonic trends"
- ✅ "More warm-up laps → better (left-to-right improvement)"
- ✅ "Longer horizon → worse (bottom-to-top degradation)"
- ✅ "Sweet spot: 3-5 laps for next-lap, MAE <1s for best races"

---

## Backup Plans

| Issue | Solution |
|-------|----------|
| Race Analytics loads slowly | Skip to lap 10 directly, don't demonstrate lap 6 |
| Diagnostics section missing | Say "No technique issues detected this lap - system only shows when needed" |
| Race Insights counterfactuals missing | Skip what-if section entirely |
| Model Validation plot unclear | Focus on aggregate metrics table instead |

---

## Questions & Answers

**Q: How real-time is this?**
> "Lap-by-lap updates with sub-second computation. Fast enough for live race engineering."

**Q: Does it work on different tracks?**
> "Yes - validated across 7 tracks (Indy, Sebring, COTA, VIR, Barber, Road America, Sonoma). Model is track-agnostic."

**Q: What data is required?**
> "Lap times (required) plus telemetry (optional for deeper analysis). Standard GR Cup data logger output."

**Q: Why laps 1-5 specifically?**
> "Trade-off: enough data to build robust baseline, but not so long that track conditions or tire state change significantly."

**Q: What if a driver is off-pace in laps 1-5?**
> "System detects outliers and can use field median as fallback, or extend warm-up period if needed."

**Q: Why is the forecast negative sometimes?**
> "Negative means that driver is predicted FASTER than you - lower lap time. Positive means they're SLOWER - higher lap time."
