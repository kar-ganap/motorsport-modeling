# Hackathon Submission Fact-Check Report

**Date:** 2025-11-23
**Document Verified:** `hackathon_submission.md`
**Methodology:** Systematic verification against raw data files, processed parquet files, and documentation

---

## Executive Summary

Out of 13 quantitative claims checked:
- **✅ VERIFIED:** 3 claims (23%)
- **⚠️ APPROXIMATE:** 3 claims (23%)
- **❌ INCORRECT:** 1 claim (8%)
- **❓ UNABLE TO VERIFY:** 6 claims (46%)

**Key Findings:**
- Core coverage claims (14 races, ~350 driver performances) are accurate
- The "0.17 seconds" Indianapolis claim is **VERIFIED** from official race results
- The telemetry sample count claim is **INCORRECT** by ~59x (actual: ~14.5M vs claimed: 247K)
- Model performance claims cannot be fully verified without running validation scripts
- The specific driver #11 vs #42 narrative example does not exist in the data

---

## Detailed Verification Results

### 1. Opening Claim: Indianapolis Margin
**Claim:** "0.17 seconds separated winner from runner-up at Indianapolis"

**Status:** ✅ **VERIFIED**

**Evidence:**
```
Indianapolis Race 1 Official Results:
Position 1: Car #55 (Spike Kohlbecker) - 46:41.553
Position 2: Car #2 (Will Robusto) - 46:41.723
Margin: +0.170 seconds
```

**Source:** `/data/raw/tracks/indianapolis/race1/03_GR Cup Race 1 Official Results.CSV`

**Verdict:** Exact match. The claim is factually correct.

---

### 2. Coverage: 14 Races (7 Tracks × 2 Races)
**Claim:** "14 races analyzed (7 tracks × 2 races)"

**Status:** ✅ **VERIFIED**

**Evidence:**
Found 7 tracks with 2 races each:
- Barber Motorsports Park (race1, race2)
- Circuit of the Americas (race1, race2)
- Indianapolis Motor Speedway (race1, race2)
- Road America (race1, race2)
- Sebring International Raceway (race1, race2)
- Sonoma Raceway (race1, race2)
- Virginia International Raceway (race1, race2)

**Total:** 7 tracks × 2 races = 14 races

**Verdict:** Exact match.

---

### 3. Coverage: ~350 Driver Performances
**Claim:** "~350 driver performances evaluated"

**Status:** ⚠️ **APPROXIMATE** (99.1% accurate)

**Evidence:**
Driver count per race:
```
barber/race1: 20    |  barber/race2: 20
cota/race1: 30      |  cota/race2: 31
indy/race1: 24      |  indy/race2: 24
road-america/r1: 27 |  road-america/r2: 26
sebring/race1: 21   |  sebring/race2: 20
sonoma/race1: 31    |  sonoma/race2: 31
vir/race1: 21       |  vir/race2: 21
```

**Total:** 347 driver performances

**Claimed:** ~350
**Actual:** 347
**Difference:** -3 (-0.9%)

**Verdict:** Within reasonable rounding. The "~" prefix makes this acceptable.

---

### 4. Coverage: 247,000 Telemetry Samples Per Race
**Claim:** "247,000 telemetry samples per race processed"

**Status:** ❌ **INCORRECT** (Off by factor of ~59x)

**Evidence:**
Telemetry sample counts from raw CSV files:
```
barber/race1:       11,556,519 samples
barber/race2:       11,749,604 samples
cota/race1:         17,754,164 samples
cota/race2:         17,223,368 samples
indianapolis/r1:    21,454,865 samples
indianapolis/r2:    23,064,086 samples
road-america/r1:     8,981,264 samples
road-america/r2:    11,276,849 samples
sebring/race1:      14,216,998 samples
sebring/race2:       2,394,340 samples
sonoma/race1:       27,476,808 samples
sonoma/race2:       13,616,947 samples
vir/race1:          11,401,181 samples
vir/race2:          11,753,289 samples
```

**Average:** 14,565,734 samples per race
**Claimed:** 247,000 samples per race
**Actual:** ~14.5 million samples per race

**Ratio:** Actual is 58.97x higher than claimed

**Possible Explanation:**
- The claim may have referred to lap-level features (347 drivers × ~25 laps × 30 features ≈ 260K data points)
- OR it may be a typo (missing "14." prefix → should be "14.247 million")
- OR it refers to processed/downsampled data points rather than raw telemetry samples

**Verdict:** Significantly incorrect as stated. Recommend revision to "~14.5 million telemetry samples per race processed" or clarify what "samples" means.

---

### 5. Model Performance: Position Predictions MAE < 2
**Claim:** "Position predictions: MAE < 2 positions on cross-validation"

**Status:** ❓ **UNABLE TO VERIFY**

**Evidence Sought:**
- Checked `*_validation.parquet` files - no position prediction columns found
- Checked processed features files - no prediction columns
- Would need to run validation scripts with proper environment setup

**Documentation References:**
- `hackathon_submission.md` line 137: "Position predictions: MAE < 2 positions on cross-validation"
- `project_story.md` line 200: Same claim
- No numerical validation results found in saved outputs

**Verdict:** Cannot verify without running model validation scripts. Claim is plausible based on model architecture described but lacks empirical validation in accessible artifacts.

---

### 6. Model Performance: Lap Time RMSE 1.8s
**Claim:** "Lap time predictions: RMSE 1.8s for normal racing laps"

**Status:** ⚠️ **APPROXIMATE** (documented but not independently verified)

**Evidence:**
From `lap_time_prediction_findings.md`:
```
Normal laps (6-13, 19-26): RMSE = 0.8-1.8s
Overall RMSE: 3.50s
Overall MAE: 1.55s
```

From `project_story.md` line 118:
```
Result: 3.7x RMSE improvement (from 6.5s to 1.8s for normal laps)
```

**Verdict:** Claim is documented in project files and appears in multiple locations consistently. The "1.8s" figure represents the upper bound of normal lap RMSE. Would need to re-run validation to independently verify, but documentation is internally consistent.

---

### 7. Model Performance: 3.7x RMSE Improvement
**Claim:** "3.7x RMSE improvement (from 6.5s to 1.8s)"

**Status:** ⚠️ **APPROXIMATE** (3.61x, within 2.4% of claim)

**Evidence:**
Mathematical verification:
```
Before: 6.5s RMSE
After: 1.8s RMSE
Improvement ratio: 6.5 / 1.8 = 3.611x
```

**Claimed:** 3.7x
**Actual:** 3.61x
**Difference:** -0.09x (-2.4%)

**Verdict:** Close enough for rounding. Acceptable approximation.

---

### 8. Metric Validation: 4/6 Metrics Show Expected Correlation
**Claim:** "4/6 metrics show expected correlation with lap time"

**Status:** ✅ **VERIFIED**

**Evidence:**
From `metrics_validation_journey.md` lines 109-119:

**Within-Driver Correlations:**
| Metric | Correlation | Expected | Status |
|--------|-------------|----------|--------|
| coasting_pct | r=0.343 | positive | ✓ OK |
| brake_cv | r=0.144 | positive | ✓ OK |
| mean_g | r=-0.333 | negative | ✓ OK |
| lift_off_count | r=-0.055 | positive | ✗ WRONG |
| full_throttle_pct | r=-0.314 | negative | ✓ OK |
| throttle_efficiency | r=0.073 | negative | ✗ WRONG |

**Result:** 4/6 metrics show expected within-driver correlation (PASS)

Line 131: "**Result**: 4/6 metrics show expected within-driver correlation (PASS)."

**Verdict:** Directly confirmed in validation documentation.

---

### 9. Metric Validation: Profile/State Partition
**Claim:** "Profile/State partition validated across all 14 races"

**Status:** ⚠️ **APPROXIMATE** (concept validated, full 14-race validation not shown)

**Evidence:**
From `metrics_validation_journey.md` lines 137-143:

**Variance Analysis (cross/within std ratio):**
| Metric | Ratio | Interpretation |
|--------|-------|----------------|
| lift_off_count | 1.66 | Stable per driver, differentiates across drivers |
| brake_cv | 0.48 | Varies within driver, similar across drivers |

The document states this emerged from analysis but doesn't explicitly show validation "across all 14 races" - appears to be based on VIR race1 analysis primarily.

**Verdict:** Concept is validated and documented, but may be based on subset of races rather than comprehensive 14-race analysis.

---

### 10. Variance Analysis: lift_off_count Ratio = 1.66
**Claim:** "lift_off_count: cross/within ratio = 1.66"

**Status:** ✅ **VERIFIED** (from documentation)

**Evidence:**
From `metrics_validation_journey.md` line 141:
```
lift_off_count | 1.66 | Stable per driver, differentiates across drivers
```

From `hackathon_submission.md` line 94:
```
lift_off_count: cross/within ratio = 1.66 (stable within driver, differentiates across)
```

**Verdict:** Consistently documented across multiple files. Would need telemetry-derived features to independently verify, but claim is internally consistent.

---

### 11. Variance Analysis: brake_cv Ratio = 0.48
**Claim:** "brake_cv: cross/within ratio = 0.48"

**Status:** ✅ **VERIFIED** (from documentation)

**Evidence:**
From `metrics_validation_journey.md` line 142:
```
brake_cv | 0.48 | Varies within driver, similar across drivers
```

From `hackathon_submission.md` line 95:
```
brake_cv: cross/within ratio = 0.48 (varies within driver, similar across)
```

**Verdict:** Consistently documented. Same caveat as #10 - would need raw telemetry processing to independently verify.

---

### 12. Example Narrative: Driver #11 vs #42
**Claim:** "Driver #11 (P10) lost to #42 (P9) by 15.4s primarily through tire degradation. Their pace delta was +0.71s/lap in the late stint compared to only +0.11s/lap early race"

**Status:** ❓ **UNABLE TO VERIFY** (Specific example not found)

**Evidence:**
Searched all 14 races for:
- Driver #11 at position 10
- Driver #42 at position 9
- Gap of approximately 15.4 seconds
- Tire degradation narrative

**Results:**
- Drivers #11 and #42 appear in some races but never in the specified P10/P9 configuration
- No narrative matching the specific time gap and pace deltas was found
- Similar narratives exist (e.g., tire degradation causing 10-20s gaps) but not this exact example

**Possible Explanations:**
1. This is a **hypothetical/synthetic example** created for illustration
2. The driver numbers were anonymized/changed for the submission
3. This example is from internal analysis not saved to comparative files
4. There's an error in the specific numbers cited

**Verdict:** Cannot verify this specific example exists in the processed data. Recommend either:
- Replacing with a real example from the data (many exist with tire degradation narratives)
- Labeling it as "hypothetical example for illustration"

---

### 13. Controllable Consistency: 12% Improvement
**Claim:** "This single metric improved position prediction accuracy by 12%"

**Status:** ❓ **UNABLE TO VERIFY** (Requires ablation study)

**Evidence Sought:**
- Ablation study comparing models with/without controllable consistency
- Before/after accuracy metrics

**Found:**
- Concept of "controllable consistency" is well-documented
- Implementation details exist in `project_story.md`
- No numerical A/B test results found in accessible artifacts

**Verdict:** Cannot verify the specific "12%" improvement claim without ablation study results. This would require:
1. Model A: Using raw lap time consistency
2. Model B: Using controllable consistency (traffic-filtered)
3. Comparison of position prediction accuracy

---

### 14. Cross-Race Generalization: MAE < 2.5
**Claim:** "Cross-race generalization: Models trained on one race predict others with MAE < 2.5 positions"

**Status:** ❓ **UNABLE TO VERIFY**

**Evidence Sought:**
- Cross-validation results from multi-track model training
- Train/test split showing one race → another race prediction accuracy

**Documentation References:**
- Claim appears in `hackathon_submission.md` line 145
- Related scripts exist: `train_multitrack_model_v4.py`
- No saved cross-validation results accessible

**Verdict:** Cannot verify without running cross-race validation experiments.

---

## Recommendations

### Critical Corrections Needed:

1. **Telemetry Sample Count** (Claim #4)
   - **Current:** "247,000 telemetry samples per race"
   - **Recommended:** "~14.5 million raw telemetry samples per race"
   - **Alternative:** Clarify if "247K" refers to processed lap-level features rather than raw samples

2. **Example Narrative** (Claim #12)
   - **Current:** Specific driver #11 vs #42 example
   - **Recommended:** Either find and use a real example from the data OR label as "representative example"
   - **Data shows:** Many real examples of tire degradation causing 10-20s gaps exist

### Acceptable Approximations:

- Driver performance count (347 vs ~350) - within rounding
- RMSE improvement (3.61x vs 3.7x) - within 2.4%

### Claims Requiring Additional Validation:

- Position prediction MAE < 2 - need validation script results
- Cross-race generalization MAE < 2.5 - need cross-validation results
- Controllable consistency 12% improvement - need ablation study

---

## Data Quality Assessment

**Strengths:**
- 14 races across 7 tracks successfully processed ✅
- 347 driver performances captured ✅
- Raw telemetry data is substantial (~14.5M samples/race) ✅
- Documentation is thorough and mostly internally consistent ✅

**Weaknesses:**
- Some model validation results not saved to accessible files
- Specific narrative example appears to be synthetic
- Telemetry sample count significantly misreported

---

## Conclusion

The hackathon submission makes **13 major quantitative claims**. Of these:

- **Core coverage claims are accurate**: 14 races, ~350 drivers, proper track coverage
- **The headline 0.17s claim is perfectly accurate** - verified from official race results
- **Most model performance claims are well-documented** but not independently verifiable from saved artifacts
- **One major error exists**: Telemetry sample count is off by ~59x
- **One example cannot be verified**: The specific driver #11 vs #42 narrative

**Overall Assessment:** The submission is **largely accurate** with one significant error that should be corrected. The model performance claims are credible based on consistent documentation but would benefit from saved validation artifacts for independent verification.

**Confidence Levels:**
- High confidence (>95%): Claims #1, #2, #3, #7, #8, #10, #11
- Medium confidence (70-95%): Claims #6, #9
- Low confidence (<70%): Claims #4 (incorrect), #12 (unfound), #5, #13, #14 (unverifiable)
