# Lap Time Prediction Model Design

**Date:** 2025-11-17
**Status:** Design Complete, Implementation Pending

---

## Objective

Predict lap times for all drivers for the remaining laps of a race, with:
- Accurate point predictions
- Uncertainty estimates that widen with prediction horizon
- Special emphasis on correctly predicting race winner

---

## Physics of the Problem

Lap times in endurance racing are influenced by several physical factors:

### Time-Increasing Factors
- **Tire degradation** - Rubber wears, grip decreases (~0.05-0.2s per lap)
- **Driver fatigue** - Consistency degrades over stint
- **Thermal degradation** - Brake/tire temps affect performance over time

### Time-Decreasing Factors
- **Fuel burn-off** - Car gets lighter (~0.03s per kg burned)
- **Track evolution** - Rubber laid down improves grip (early race)

### Race-Specific Factors
- **Traffic** - Slower cars, blue flags cost time
- **Drafting/slipstream** - Following cars benefit on straights
- **Defensive driving** - Leader may drive conservatively
- **Attack mode** - Chasing drivers push harder, risking tire wear

**Net effect:** Lap times generally increase over a stint due to tire degradation dominating fuel benefit.

---

## Model Architecture

### Two-Model Approach

#### Model 1: Linear Baseline
Simple, interpretable benchmark:

```python
lap_time = baseline + degradation × lap_number - fuel_benefit × (total_laps - lap)
```

- Per-driver parameters (baseline, degradation rate)
- Fast to fit
- Provides interpretable coefficients

#### Model 2: Telemetry-Enhanced (Gradient Boosting)
XGBoost/LightGBM with rich feature set including race context.

---

## Feature Engineering

### Core Features
| Feature | Description | Source |
|---------|-------------|--------|
| `lap_number` | Current lap in race | Lap times |
| `stint_lap` | Lap within current tire stint | Derived |
| `driver_id` | Driver identifier (encoded) | Lap times |

### Telemetry Features (Rolling 3-lap averages)
| Feature | Description | Source |
|---------|-------------|--------|
| `avg_throttle_pct` | Mean throttle application | Telemetry |
| `avg_brake_pulses` | Brake confidence indicator | Telemetry |
| `avg_smoothness` | Steering jerk (fatigue indicator) | Telemetry |
| `avg_full_throttle_pct` | Aggression indicator | Telemetry |
| `throttle_timing` | Time to full throttle after corners | Telemetry |

### Race Context Features (Critical for Competition)
| Feature | Description | Rationale |
|---------|-------------|-----------|
| `position` | Current race position | Leaders drive differently than chasers |
| `gap_to_ahead` | Seconds to car in front | Small gap → pushing → faster but more wear |
| `gap_to_behind` | Seconds to car behind | Small gap → defending or being hunted |
| `gap_to_leader` | Seconds behind P1 | Overall race context |
| `laps_remaining` | Laps left in race | Affects conservation vs push decision |
| `is_fighting` | Gap < 1s to adjacent car | Direct combat indicator |

### Derived Features
| Feature | Description |
|---------|-------------|
| `gap_delta_ahead` | Change in gap to car ahead (last 3 laps) |
| `gap_delta_behind` | Change in gap to car behind |
| `position_change_recent` | Positions gained/lost in last 5 laps |
| `fuel_load_estimate` | Estimated remaining fuel (linear model) |

---

## Capturing Competitive Dynamics

### Why Race Context Matters

The gap features implicitly encode competitive strategy:

- **Small `gap_to_behind` + fast lap** → Driver defending position
- **Small `gap_to_ahead` + very fast lap** → Driver attacking for position
- **Shrinking `gap_to_ahead`** → You're faster OR opponent is struggling
- **Growing `gap_to_behind`** → You're pulling away OR opponent gave up

The model learns these correlations without needing explicit strategy labels.

### What We're NOT Modeling (Out of Scope)
- Pit stop timing optimization
- Tire compound selection
- Safety car probability
- Mechanical failures

---

## Loss Function Design

### Standard Loss (Baseline)
```python
MSE = mean((y_true - y_pred)²)
```

### Position-Weighted Loss (Recommended)
Penalize errors on front-runners more heavily:

```python
def position_weighted_loss(y_true, y_pred, positions):
    """
    Weight errors by position importance.
    P1 = 1.0, P2 = 0.95, ..., P19 = 0.10
    """
    weights = np.maximum(0.1, 1.0 - (positions - 1) * 0.05)
    return np.mean(weights * (y_true - y_pred)**2)
```

### Rationale
- Getting the winner wrong has bigger implications than getting P15 wrong
- Race engineers care most about their car and immediate competitors
- Hackathon judges will evaluate winner prediction quality

---

## Evaluation Metrics

### Primary Metrics
| Metric | Target | Description |
|--------|--------|-------------|
| RMSE (Race 1) | < 1.0s | In-sample fit quality |
| RMSE (Race 2) | < 1.5s | Out-of-sample generalization |
| Winner Accuracy | > 80% | Correctly predict winner from lap N |

### Secondary Metrics
| Metric | Description |
|--------|-------------|
| Top-3 Accuracy | Correctly predict podium from lap 15 |
| Position RMSE | Error in predicted final positions |
| Calibration | Do 90% CIs contain 90% of actuals? |

### Winner Prediction Metric
```python
def winner_accuracy_from_lap(predictions, actuals, from_lap):
    """
    Did we predict the right winner based on data up to from_lap?

    predictions: dict of {driver: [predicted_times_for_remaining_laps]}
    actuals: dict of {driver: [actual_times_for_remaining_laps]}
    """
    pred_totals = {d: sum(times) for d, times in predictions.items()}
    actual_totals = {d: sum(times) for d, times in actuals.items()}

    pred_winner = min(pred_totals, key=pred_totals.get)
    actual_winner = min(actual_totals, key=actual_totals.get)

    return pred_winner == actual_winner
```

---

## Prediction with Uncertainty

### Approach: Quantile Regression
Train separate models for 10th, 50th, 90th percentiles:

```python
# Point prediction
model_50 = LGBMRegressor(objective='quantile', alpha=0.5)

# Confidence bounds
model_10 = LGBMRegressor(objective='quantile', alpha=0.1)
model_90 = LGBMRegressor(objective='quantile', alpha=0.9)
```

### Expected Uncertainty Growth
| Prediction Horizon | Expected 80% CI Width |
|--------------------|----------------------|
| Next lap | ±0.3s |
| +5 laps | ±0.8s |
| +10 laps | ±1.5s |
| End of race (from lap 10) | ±3.0s |

### Implementation
```python
def predict_remaining_race(model, current_lap, total_laps, features):
    """
    Predict all remaining laps with confidence intervals.
    """
    predictions = []

    for future_lap in range(current_lap + 1, total_laps + 1):
        # Update features for future lap
        future_features = update_features_for_lap(features, future_lap)

        # Get point estimate and bounds
        pred_50 = model_50.predict(future_features)
        pred_10 = model_10.predict(future_features)
        pred_90 = model_90.predict(future_features)

        predictions.append({
            'lap': future_lap,
            'prediction': pred_50,
            'lower_bound': pred_10,
            'upper_bound': pred_90,
            'horizon': future_lap - current_lap
        })

    return predictions
```

---

## Training Strategy

### Data Split
1. **Train:** Race 1, laps 1-20 (all drivers)
2. **Validation:** Race 1, laps 21-26 (same-race holdout)
3. **Test:** Race 2, all laps (out-of-sample generalization)

### Why This Split?
- Validation set tests extrapolation within same race conditions
- Test set tests generalization to different race (weather, track state, etc.)
- If Race 2 performance is poor, model is overfitting to Race 1 specifics

### Cross-Validation (Optional Enhancement)
- Leave-one-driver-out CV within Race 1
- Tests generalization to "unseen" driving styles

---

## Implementation Plan

### Phase 1: Data Preparation
1. Load lap time data for Race 1 and Race 2
2. Compute cumulative times and positions per lap
3. Calculate gaps to ahead/behind/leader
4. Extract per-lap telemetry summaries (Tier 1 metrics)
5. Create feature matrix

### Phase 2: Baseline Model
1. Implement linear degradation model
2. Fit per-driver parameters
3. Evaluate RMSE on validation and test sets
4. Establish baseline performance

### Phase 3: Enhanced Model
1. Engineer all features (telemetry + race context)
2. Train LightGBM with position-weighted loss
3. Train quantile models for uncertainty
4. Compare to baseline

### Phase 4: Evaluation
1. Compute all metrics (RMSE, winner accuracy, calibration)
2. Visualize predictions vs actuals
3. Analyze failure cases
4. Document results

---

## Success Criteria

### Minimum Viable (MVP)
- [ ] Race 1 RMSE < 1.0s
- [ ] Race 2 RMSE < 1.5s
- [ ] Winner prediction accuracy > 70% from lap 15

### Good
- [ ] Race 2 RMSE < 1.2s
- [ ] Winner accuracy > 80% from lap 15
- [ ] Top-3 accuracy > 60% from lap 15

### Excellent
- [ ] Race 2 RMSE < 0.8s
- [ ] Winner accuracy > 90% from lap 10
- [ ] Well-calibrated uncertainty estimates

---

## Files to Create

### Source Code
- `src/motorsport_modeling/models/lap_time_predictor.py` - Main model classes
- `src/motorsport_modeling/models/feature_engineering.py` - Feature computation

### Scripts
- `scripts/train_lap_predictor.py` - Training pipeline
- `scripts/evaluate_lap_predictor.py` - Evaluation and visualization

### Outputs
- `data/processed/race1_features.parquet` - Engineered features
- `data/processed/race2_features.parquet`
- `models/lap_predictor_baseline.pkl` - Trained baseline
- `models/lap_predictor_enhanced.pkl` - Trained enhanced model
- `outputs/lap_prediction_results.png` - Visualization

---

## Open Questions

1. **Pit stops:** Do we have pit stop data? Would need to handle stint resets.
2. **Weather:** Weather files exist - should we include conditions?
3. **Class differences:** Are all drivers in same class or mixed?
4. **DNFs:** How to handle drivers who don't finish?

---

## References

- Toyota GR Cup data dictionary (if available)
- Tire degradation models in F1 literature
- Time series forecasting with LightGBM
