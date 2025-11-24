"""
Test Counterfactual Model with Telemetry-Based Traffic Detection

Compares model performance with and without traffic detection to validate the feature.
"""

from pathlib import Path
import pandas as pd
import numpy as np
from motorsport_modeling.data.telemetry_loader import load_telemetry, load_lap_times
from motorsport_modeling.counterfactual.feature_extractor import extract_race_features
from motorsport_modeling.counterfactual.lap_time_model import LapTimeModel

# Load Indianapolis race1 data
data_dir = Path('data/raw/tracks/indianapolis/race1')

print('='*70)
print('COUNTERFACTUAL MODEL TEST: WITH vs WITHOUT TRAFFIC DETECTION')
print('='*70)
print()

# Load data
print('Loading race data...')
lap_times = load_lap_times(data_dir)
telemetry = load_telemetry(data_dir, laps=list(range(1, 21)), pivot_to_wide=True, verbose=False)
print(f'  Lap times: {len(lap_times)} rows, {lap_times["vehicle_number"].nunique()} drivers')
print(f'  Telemetry: {len(telemetry)} rows, {telemetry["vehicle_number"].nunique()} drivers')
print()

# TEST 1: Extract features WITHOUT telemetry (traffic will be 0)
print('-'*70)
print('TEST 1: Feature extraction WITHOUT telemetry (no traffic detection)')
print('-'*70)
features_no_traffic = extract_race_features(lap_times, stint='full', telemetry=None)
print(f'Extracted features for {len(features_no_traffic)} drivers')
print()
print('Traffic laps summary (without telemetry):')
print(f'  Min: {features_no_traffic["controllable_traffic_laps"].min()}')
print(f'  Max: {features_no_traffic["controllable_traffic_laps"].max()}')
print(f'  Mean: {features_no_traffic["controllable_traffic_laps"].mean():.2f}')
print(f'  Non-zero count: {(features_no_traffic["controllable_traffic_laps"] > 0).sum()}')
print()

# TEST 2: Extract features WITH telemetry (traffic should be detected)
print('-'*70)
print('TEST 2: Feature extraction WITH telemetry (GPS-based traffic detection)')
print('-'*70)
features_with_traffic = extract_race_features(lap_times, stint='full', telemetry=telemetry)
print(f'Extracted features for {len(features_with_traffic)} drivers')
print()
print('Traffic laps summary (with telemetry):')
print(f'  Min: {features_with_traffic["controllable_traffic_laps"].min()}')
print(f'  Max: {features_with_traffic["controllable_traffic_laps"].max()}')
print(f'  Mean: {features_with_traffic["controllable_traffic_laps"].mean():.2f}')
print(f'  Non-zero count: {(features_with_traffic["controllable_traffic_laps"] > 0).sum()}')
print()

# Show per-driver traffic comparison
print('Per-driver traffic detection:')
print('-'*70)
comparison = pd.DataFrame({
    'vehicle': features_with_traffic['vehicle_number'],
    'position': features_with_traffic['final_position'],
    'traffic_laps': features_with_traffic['controllable_traffic_laps'],
    'baseline_pace': features_with_traffic['baseline_pace'],
    'avg_lap_time': features_with_traffic['avg_lap_time'],
    'lap_time_delta': features_with_traffic['lap_time_delta'],
})
comparison = comparison.sort_values('position')
print(comparison.to_string(index=False))
print()

# TEST 3: Train model WITHOUT traffic
print('='*70)
print('TEST 3: Train model WITHOUT traffic detection')
print('='*70)
model_no_traffic = LapTimeModel()
model_no_traffic.fit(features_no_traffic, verbose=True)
print()

# TEST 4: Train model WITH traffic
print('='*70)
print('TEST 4: Train model WITH traffic detection')
print('='*70)
model_with_traffic = LapTimeModel()
model_with_traffic.fit(features_with_traffic, verbose=True)
print()

# COMPARISON
print('='*70)
print('COMPARISON: Impact of Traffic Detection')
print('='*70)
print()

print('Model WITHOUT traffic:')
print(f'  R² Score: {model_no_traffic.validation.r2_score:.3f}')
print(f'  Cross-Val R² (LOO): {model_no_traffic.validation.cv_r2_mean:.3f} ± {model_no_traffic.validation.cv_r2_std:.3f}')
print(f'  MAE: {model_no_traffic.validation.mae:.3f}s')
print(f'  Traffic coefficient: {model_no_traffic.model.coef_[2]:.4f}')
print()

print('Model WITH traffic:')
print(f'  R² Score: {model_with_traffic.validation.r2_score:.3f}')
print(f'  Cross-Val R² (LOO): {model_with_traffic.validation.cv_r2_mean:.3f} ± {model_with_traffic.validation.cv_r2_std:.3f}')
print(f'  MAE: {model_with_traffic.validation.mae:.3f}s')
print(f'  Traffic coefficient: {model_with_traffic.model.coef_[2]:.4f}')
print()

# Calculate improvement
r2_improvement = model_with_traffic.validation.r2_score - model_no_traffic.validation.r2_score
mae_improvement = model_no_traffic.validation.mae - model_with_traffic.validation.mae

print('IMPROVEMENT:')
print(f'  Δ R²: {r2_improvement:+.3f} ({r2_improvement/model_no_traffic.validation.r2_score*100:+.1f}%)')
print(f'  Δ MAE: {mae_improvement:+.3f}s ({mae_improvement/model_no_traffic.validation.mae*100:+.1f}%)')
print()

if features_with_traffic['controllable_traffic_laps'].sum() > 0:
    print('✓ Traffic detection is working!')
    print(f'  Detected traffic on {(features_with_traffic["controllable_traffic_laps"] > 0).sum()} drivers')
    print(f'  Average {features_with_traffic["controllable_traffic_laps"].mean():.1f} laps in traffic per driver')
else:
    print('✗ Traffic detection returned all zeros - may need debugging')
    print('  Check if telemetry has lap_distance column')
    print('  Check if time windows and distance thresholds are appropriate')

print()
print('='*70)
print('TEST COMPLETE')
print('='*70)
