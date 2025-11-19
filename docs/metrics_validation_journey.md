# Metrics Validation Journey

## Executive Summary

This document captures the iterative process of developing and validating technique metrics for the RaceCraft AI real-time coaching system. What began as a straightforward implementation revealed critical insights about metric design, validation methodology, and the fundamental difference between "driver profiling" and "state monitoring" features.

**Key Outcome**: We discovered that metrics naturally partition into two categories based on their variance structure, enabling a more sophisticated two-tier coaching architecture than originally planned.

---

## Timeline and Key Decisions

### Phase 1: Original Plan

**Initial Milestone Plan:**
1. Validate data quality across all tracks
2. Create unified telemetry loader
3. Implement Tier 1 technique metrics (5 metrics)
4. Build technique degradation detector
5. Create actionable recommendations system
6. Build real-time dashboard simulation

**Original Tier 1 Metrics Proposal:**
1. Consistency (lap time σ)
2. Coasting % (neither throttle nor brake)
3. Braking smoothness (oscillations per event)
4. Throttle timing (apex to full throttle)
5. G-force utilization (mean combined G)

### Phase 2: P0 Data Quality Audit

**Trigger**: User asked "we only explored part of the Indy dataset early on... Have we exercised same level of scrutiny to our entire dataset?"

**Actions Taken:**
- Created `scripts/audit_all_tracks_data_quality.py`
- Discovered telemetry is in LONG format (not wide as assumed)
- Found signal availability varies by track:
  - Barber, Indianapolis: 12 signals (with GPS)
  - Others: 9 signals (no GPS, `ath` instead of `aps`)
  - Sebring R2: JSON format with lap 32768 corruption

**Critical Documentation Review:**
- Read `datasets_notes.md` for known issues
- Key gotchas: `meta_time` vs `timestamp`, lap 32768 corruption, vehicle number 000

**Outcome**: Created unified `telemetry_loader.py` handling all format variations.

### Phase 3: Semantic EDA

**Trigger**: User asked for analysis "beyond data loading/basic hygiene... looking at variate distributions, outliers, missing values"

**Key Findings** (`scripts/eda_telemetry.py`):
- **Sampling rate disparity**: `speed/nmot/lap_distance` at ~5k samples vs ~20k for other signals (1/3 rate)
- **Physical sanity**: 90.5% of braking events show correct deceleration correlation
- **Driver variability**: CV of mean speed across drivers = 3.1% (reasonable spread)

### Phase 4: Initial Metrics Implementation and Validation Failure

**First Implementation:**
- Created `src/motorsport_modeling/metrics/tier1_metrics.py`
- Implemented all 5 proposed metrics

**Initial Validation Results** (P1 vs P19 comparison):
- P1 wins on 3 of 5 metrics (target was 4)
- Concerning: some metrics didn't differentiate as expected

**Critical User Challenge:**
> "Can you help me understand if 'metrics differentiate drivers but don't perfectly correlate with race position' then how do we know 'metrics are working' and more importantly those would be predictive of our output figures of merit?"

This question fundamentally changed our validation approach.

### Phase 5: Proper Validation Methodology

**Insight**: "Differentiating drivers" is weak validation. The real test is whether metrics **predict lap time**.

**New Validation Framework:**
1. **Within-driver correlation**: When a driver's metric changes lap-to-lap, does their lap time change accordingly?
2. **Cross-driver correlation**: Does metric ranking predict pace ranking across drivers?

**Initial Results with Original Metrics:**
- `coasting_pct`: OK (r=0.343, rho=0.458*)
- `mean_g`: OK (r=-0.333, rho=0.449*)
- `brake_osc`: WRONG (r=-0.237, expected positive)
- `apex_to_throttle`: WRONG (r=-0.107, expected positive)

**Conclusion**: 2 of 4 metrics had wrong correlation direction - they were measuring the wrong thing.

### Phase 6: Research-Backed Metric Redesign

**Web Research Findings:**

For throttle metrics, industry sources consistently emphasized:
- "Throttle should only be going up, never down, 99% of the time" - lift-offs indicate traction management failure
- F1 uses throttle engagement × top speed as official score
- Full throttle percentage correlates with lap time (Monaco 42%, Spa 70%)

**Redesigned Throttle Metric:**
- Replaced "apex to throttle timing" with three research-validated metrics:
  1. **Lift-off count**: Number of throttle decreases during acceleration (wheelspin indicator)
  2. **Full throttle percentage**: Time at >90% throttle (F1-validated)
  3. **Throttle efficiency**: Correlation of throttle vs longitudinal G

**Redesigned Braking Metric:**
- Replaced "oscillations per event" with **peak brake pressure CV**
- Rationale: Consistent peak pressures indicate repeatable technique; oscillation counting was capturing aggressive (fast) driving as "bad"

### Phase 7: Final Validation Results

**Within-Driver Correlations (metric change → lap time change):**

| Metric | Correlation | Expected | Status |
|--------|-------------|----------|--------|
| coasting_pct | r=0.343 | positive | OK |
| brake_cv | r=0.144 | positive | OK |
| mean_g | r=-0.333 | negative | OK |
| lift_off_count | r=-0.055 | positive | WRONG |
| full_throttle_pct | r=-0.314 | negative | OK |
| throttle_efficiency | r=0.073 | negative | WRONG |

**Cross-Driver Correlations (metric rank → pace rank):**

| Metric | Spearman rho | p-value | Significant |
|--------|-------------|---------|-------------|
| coasting_pct | 0.458 | 0.032 | Yes* |
| mean_g | 0.449 | 0.036 | Yes* |
| lift_off_count | 0.506 | 0.016 | Yes* |
| full_throttle_pct | -0.385 | 0.077 | Marginal |
| brake_cv | -0.238 | 0.287 | No |
| throttle_efficiency | 0.243 | 0.275 | No |

**Result**: 4/6 metrics show expected within-driver correlation (PASS).

### Phase 8: Discovering the Two-Tier Feature Structure

**Puzzling Observation**: Some metrics work only within-driver, others only cross-driver.

**Variance Analysis** (cross/within std ratio):

| Metric | Ratio | Interpretation |
|--------|-------|----------------|
| lift_off_count | 1.66 | Stable per driver, differentiates across drivers |
| brake_cv | 0.48 | Varies within driver, similar across drivers |

**Key Insight**: These metrics capture fundamentally different phenomena:

1. **Profiling Features** (high cross/within ratio): Stable traits that characterize a driver's skill level
   - `lift_off_count` - traction management ability
   - `mean_combined_g` - grip utilization ability

2. **State Features** (low cross/within ratio): Dynamic measures that fluctuate with fatigue, confidence, conditions
   - `brake_cv` - current braking consistency
   - `coasting_pct` - current commitment level

---

## Validated Metrics Summary

### Final Metric Set

| Metric | Type | Within-Driver | Cross-Driver | Use Case |
|--------|------|---------------|--------------|----------|
| `coasting_pct` | State | r=0.343 ✓ | rho=0.458* ✓ | Real-time alerts |
| `mean_combined_g` | Profile | r=-0.333 ✓ | rho=0.449* ✓ | Skill assessment |
| `full_throttle_pct` | Both | r=-0.314 ✓ | rho=-0.385 | Commitment tracking |
| `lift_off_count` | Profile | r=-0.055 | rho=0.506* ✓ | Skill assessment |
| `brake_cv` | State | r=0.144 ✓ | rho=-0.238 | Fatigue detection |

### Metrics Removed/Deprecated

| Original Metric | Reason for Removal |
|-----------------|-------------------|
| Brake oscillations | Correlated negatively - fast drivers are "oscillating" (trail braking) |
| Apex-to-throttle timing | Wrong correlation - speed of throttle application ≠ quality |
| Throttle efficiency | Confounded by gear, drag; correlation wrong direction |

---

## Key Learnings

### 1. Validation Must Match Use Case

"Does metric differentiate drivers?" is insufficient. Must test:
- Does it predict the outcome we care about (lap time)?
- Does it work within-driver (for real-time coaching)?
- Does it work cross-driver (for benchmarking)?

### 2. Domain Knowledge is Critical

Initial metrics were intuitively reasonable but empirically wrong:
- **Brake oscillations**: We assumed smooth = good. Actually, controlled oscillations from trail braking are fast technique.
- **Throttle timing**: We assumed faster = better. Actually, progressive application is better than jamming throttle.

Research sources (RACER, OptimumG, HP Academy) provided validated patterns.

### 3. Variance Structure Reveals Feature Purpose

The cross/within variance ratio naturally partitions features:
- High ratio (>1.5): Profiling features (stable traits)
- Low ratio (<0.7): State features (dynamic monitoring)

This wasn't designed - it emerged from data analysis.

### 4. Two-Tier Architecture is More Valuable

Originally sought metrics that work "both ways." Discovering they partition by purpose enables:
- Better real-time alerts (compare to driver's own baseline)
- Better benchmarking (compare stable traits across field)
- Clearer coaching messages (skill deficit vs current state)

---

## Implications for Path Forward

### Architecture Changes

The original plan assumed uniform metrics. Now we need:

```
DriverProfile (computed once per session)
├── Profiling Features
│   ├── lift_off_count (mean)
│   ├── mean_combined_g (mean)
│   └── full_throttle_pct (mean)
└── State Baselines
    ├── brake_cv (mean, std)
    └── coasting_pct (mean, std)

RealTimeMonitor (computed per lap)
├── Compare state features to driver's own baseline
├── Alert when >2σ deviation
└── Generate specific recommendations
```

### Recommendation System Design

**Profile-based (post-session):**
```
"Driver #8: Your lift-off count (2.37/application) is 2x field average.
 Focus: Progressive throttle application on corner exit."
```

**State-based (real-time):**
```
"Lap 15: Brake CV jumped to 52% (your baseline: 35%).
 Action: Check fatigue, consider mental reset."
```

### Revised Milestones

The two-tier discovery fundamentally changes what we need to build. Here's the revised plan:

#### Completed
1. ~~P0: Validate data quality~~ ✓
2. ~~Create unified telemetry loader~~ ✓
3. ~~Implement Tier 1 metrics~~ ✓ (with validation)
4. ~~Document findings~~ ✓

#### Revised Remaining Work

**5. Build DriverProfile system** (NEW)
- Compute profiling features once per session (lift_off_count, mean_g, full_throttle_pct)
- Establish state feature baselines per driver (brake_cv mean/std, coasting_pct mean/std)
- Store for comparison during race
- Compare against field for benchmarking

**6. Build StateMonitor / degradation detector** (CHANGED)
- Original: Generic degradation detection
- Now: Compare state features against driver's OWN baseline (not field average)
- Alert types:
  - Sudden: >2σ deviation from baseline
  - Progressive: Trending worse over 3+ laps
- Only monitor state features (brake_cv, coasting_pct), not profiling features

**7. Create two-tier recommendations system** (CHANGED)
- Original: Single recommendation type
- Now: Two distinct recommendation flows:

  **Profile recommendations (post-session/between stints):**
  - Compare driver's profiling features to field
  - "Your lift-offs are 2x field average → Focus on progressive throttle"
  - Actionable training feedback

  **State recommendations (real-time):**
  - Compare current lap to driver's own baseline
  - "Brake CV up 50% from your baseline → Check fatigue"
  - Immediate actionable alerts

**8. Build real-time dashboard** (CHANGED)
- Original: Single metrics view
- Now: Split display:
  - **Profile panel**: Driver's stable traits vs field (spider chart?)
  - **State panel**: Current lap vs baseline with trend arrows
  - **Alerts**: State-based warnings with specific actions
  - **Historical**: Show if current state deviation has happened before and what followed

#### Why These Changes Matter

| Original Assumption | Reality | Impact |
|---------------------|---------|--------|
| All metrics work uniformly | Metrics partition by variance structure | Need two parallel systems |
| Compare to field average | Profile: compare to field; State: compare to self | Different baselines for different features |
| Single recommendation type | Profile needs training focus; State needs immediate action | Different message formats |
| Generic degradation alert | State degradation meaningful; Profile "degradation" is noise | Only monitor state features for alerts |

#### Effort Estimate Changes

| Component | Original | Revised | Delta |
|-----------|----------|---------|-------|
| Degradation detector | 1 system | 1 system (state only) | Same |
| Recommendations | 1 type | 2 types (profile + state) | +50% |
| Dashboard | 1 view | 2 panels + split logic | +30% |
| **New: DriverProfile** | N/A | New component | +New |

Overall: ~30-40% more work, but significantly more valuable output.

### Technical Debt

- `throttle_efficiency` metric still broken - needs rethinking or removal
- Need to test metrics on other tracks (currently validated on Indianapolis only)
- JSON format (Sebring R2) still has partial support

---

## Appendix: Code Artifacts

### Key Files Created/Modified

| File | Purpose |
|------|---------|
| `src/motorsport_modeling/data/telemetry_loader.py` | Unified data loading |
| `src/motorsport_modeling/metrics/tier1_metrics.py` | Metric implementations |
| `scripts/validate_metrics_properly.py` | Validation framework |
| `scripts/eda_telemetry.py` | Semantic EDA |
| `scripts/audit_all_tracks_data_quality.py` | P0 data audit |

### Validation Commands

```bash
# Run full validation
uv run python scripts/validate_metrics_properly.py

# Run EDA
uv run python scripts/eda_telemetry.py
```

---

## References

- RACER: "Leveraging Data: Throttle Application" (2014)
- OptimumG: "On the Throttle"
- HP Academy: "Going Faster with Data Analysis"
- Formula 1: "Race Performance Ratings Explained - Throttle" (2015)
- Grassroots Motorsports: "How to Diagnose Those Data Traces"
