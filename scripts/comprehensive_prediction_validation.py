"""
Comprehensive validation of relative performance predictions.

Tests:
1. All laps (not just samples)
2. Different training window sizes
3. Position-stratified analysis (frontrunners vs midfield vs backmarkers)
4. Cross-race validation (Race 1 -> Race 2)
5. Cross-track validation (Indianapolis -> VIR)
6. Per-driver breakdown
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple
from motorsport_modeling.models.feature_engineering import prepare_race_features


def load_and_prepare_data(
    lap_time_file: Path,
    total_laps: int,
    endurance_file: Path = None
) -> pd.DataFrame:
    """Load and prepare data with relative performance."""
    data = prepare_race_features(
        lap_time_file=lap_time_file,
        total_laps=total_laps,
        endurance_file=endurance_file if endurance_file and endurance_file.exists() else None,
        verbose=False
    )

    # Filter
    data = data[data['lap_time'].notna()].copy()
    if 'is_under_yellow' in data.columns:
        data = data[data['is_under_yellow'] == 0].copy()

    # Add relative time
    field_median = data.groupby('lap')['lap_time'].median()
    data['field_median'] = data['lap'].map(field_median)
    data['relative_time'] = data['lap_time'] - data['field_median']

    # Filter outliers (2 std per driver)
    def filter_outliers(group):
        mean = group['relative_time'].mean()
        std = group['relative_time'].std()
        if std > 0:
            return group[abs(group['relative_time'] - mean) <= 2 * std]
        return group

    data = data.groupby('vehicle_number', group_keys=False).apply(filter_outliers)

    # Add lag features
    data = data.sort_values(['vehicle_number', 'lap'])
    data['prev_relative'] = data.groupby('vehicle_number')['relative_time'].shift(1)

    return data


def predict_relative_performance(
    train_data: pd.DataFrame,
    test_data: pd.DataFrame,
    alpha: float = 0.3
) -> np.ndarray:
    """
    Predict relative performance using weighted average.

    pred = alpha * prev_relative + (1 - alpha) * driver_mean
    """
    # Compute driver means from training data
    driver_means = train_data.groupby('vehicle_number')['relative_time'].mean().to_dict()

    # Apply to test data
    test = test_data.copy()
    test['driver_mean'] = test['vehicle_number'].map(driver_means).fillna(0)
    test['prev_relative'] = test['prev_relative'].fillna(test['driver_mean'])

    predictions = alpha * test['prev_relative'].values + (1 - alpha) * test['driver_mean'].values
    return predictions


def expanding_window_validation(
    data: pd.DataFrame,
    min_train_laps: int = 5,
    alpha: float = 0.3
) -> Dict:
    """Run expanding window validation and return detailed results."""
    max_lap = int(data['lap'].max())

    results = []

    for train_end in range(min_train_laps, max_lap):
        predict_lap = train_end + 1

        train = data[data['lap'] <= train_end]
        test = data[data['lap'] == predict_lap]

        if len(test) == 0:
            continue

        # Predict
        predictions = predict_relative_performance(train, test, alpha)
        actuals = test['relative_time'].values
        positions = test['position'].values
        vehicles = test['vehicle_number'].values

        # Store per-prediction results
        for i in range(len(predictions)):
            results.append({
                'lap': predict_lap,
                'vehicle_number': vehicles[i],
                'position': positions[i],
                'actual': actuals[i],
                'predicted': predictions[i],
                'error': actuals[i] - predictions[i],
                'abs_error': abs(actuals[i] - predictions[i])
            })

    return pd.DataFrame(results)


def main():
    print("=" * 80)
    print("COMPREHENSIVE PREDICTION VALIDATION")
    print("=" * 80)

    # =================================================================
    # Load all data
    # =================================================================
    base_dir = Path(__file__).parent.parent / "data" / "raw" / "tracks"

    # Indianapolis Race 1
    indy_r1 = load_and_prepare_data(
        base_dir / "indianapolis" / "race1" / "R1_indianapolis_motor_speedway_lap_time.csv",
        total_laps=26,
        endurance_file=base_dir / "indianapolis" / "race1" / "23_AnalysisEnduranceWithSections_Race 1.CSV"
    )

    # Indianapolis Race 2
    indy_r2 = load_and_prepare_data(
        base_dir / "indianapolis" / "race2" / "R2_indianapolis_motor_speedway_lap_time.csv",
        total_laps=26,
        endurance_file=base_dir / "indianapolis" / "race2" / "23_AnalysisEnduranceWithSections_Race 2.CSV"
    )

    # VIR Race 1 (if available)
    vir_file = base_dir / "vir" / "race1" / "vir_lap_time_R1.csv"
    vir_data = None
    if vir_file.exists():
        try:
            vir_data = load_and_prepare_data(vir_file, total_laps=30)
        except Exception as e:
            print(f"Could not load VIR data: {e}")

    # =================================================================
    # TEST 1: Within-race validation (Indianapolis Race 1)
    # =================================================================
    print("\n" + "=" * 80)
    print("TEST 1: WITHIN-RACE VALIDATION (Indianapolis Race 1)")
    print("=" * 80)

    results_r1 = expanding_window_validation(indy_r1, min_train_laps=5)

    overall_rmse = np.sqrt((results_r1['error'] ** 2).mean())
    overall_mae = results_r1['abs_error'].mean()

    print(f"\nOverall Results:")
    print(f"  RMSE: {overall_rmse:.3f}s")
    print(f"  MAE:  {overall_mae:.3f}s")
    print(f"  Samples: {len(results_r1)}")

    # =================================================================
    # TEST 2: Position-stratified analysis
    # =================================================================
    print("\n" + "-" * 80)
    print("TEST 2: POSITION-STRATIFIED ANALYSIS")
    print("-" * 80)

    # Define position groups
    results_r1['pos_group'] = pd.cut(
        results_r1['position'],
        bins=[0, 5, 10, 15, 25],
        labels=['P1-5', 'P6-10', 'P11-15', 'P16+']
    )

    print("\nRMSE by Position Group:")
    for group in ['P1-5', 'P6-10', 'P11-15', 'P16+']:
        group_data = results_r1[results_r1['pos_group'] == group]
        if len(group_data) > 0:
            rmse = np.sqrt((group_data['error'] ** 2).mean())
            mae = group_data['abs_error'].mean()
            print(f"  {group}: RMSE = {rmse:.3f}s, MAE = {mae:.3f}s (n={len(group_data)})")

    # =================================================================
    # TEST 3: Per-lap analysis
    # =================================================================
    print("\n" + "-" * 80)
    print("TEST 3: PER-LAP ANALYSIS")
    print("-" * 80)

    lap_stats = results_r1.groupby('lap').agg({
        'error': lambda x: np.sqrt((x ** 2).mean()),
        'abs_error': 'mean',
        'vehicle_number': 'count'
    }).rename(columns={'error': 'rmse', 'abs_error': 'mae', 'vehicle_number': 'n'})

    print("\nBest laps (lowest RMSE):")
    best_laps = lap_stats.nsmallest(5, 'rmse')
    for lap, row in best_laps.iterrows():
        print(f"  Lap {lap}: RMSE = {row['rmse']:.3f}s (n={row['n']})")

    print("\nWorst laps (highest RMSE):")
    worst_laps = lap_stats.nlargest(5, 'rmse')
    for lap, row in worst_laps.iterrows():
        print(f"  Lap {lap}: RMSE = {row['rmse']:.3f}s (n={row['n']})")

    # =================================================================
    # TEST 4: Different training window sizes
    # =================================================================
    print("\n" + "-" * 80)
    print("TEST 4: TRAINING WINDOW SIZE ANALYSIS")
    print("-" * 80)

    for min_laps in [3, 5, 8, 10]:
        results = expanding_window_validation(indy_r1, min_train_laps=min_laps)
        rmse = np.sqrt((results['error'] ** 2).mean())
        print(f"  Min train laps = {min_laps}: RMSE = {rmse:.3f}s (n={len(results)})")

    # =================================================================
    # TEST 5: Per-driver analysis
    # =================================================================
    print("\n" + "-" * 80)
    print("TEST 5: PER-DRIVER ANALYSIS")
    print("-" * 80)

    driver_stats = results_r1.groupby('vehicle_number').agg({
        'error': lambda x: np.sqrt((x ** 2).mean()),
        'abs_error': 'mean',
        'position': 'mean'
    }).rename(columns={'error': 'rmse', 'abs_error': 'mae', 'position': 'avg_pos'})

    driver_stats = driver_stats.sort_values('rmse')

    print("\nBest predicted drivers:")
    for veh, row in driver_stats.head(5).iterrows():
        print(f"  #{int(veh)}: RMSE = {row['rmse']:.3f}s, avg pos = {row['avg_pos']:.1f}")

    print("\nWorst predicted drivers:")
    for veh, row in driver_stats.tail(5).iterrows():
        print(f"  #{int(veh)}: RMSE = {row['rmse']:.3f}s, avg pos = {row['avg_pos']:.1f}")

    # Correlation between avg position and prediction error
    from scipy import stats
    corr, p = stats.spearmanr(driver_stats['avg_pos'], driver_stats['rmse'])
    print(f"\nCorrelation (avg_position vs RMSE): rho = {corr:.3f}, p = {p:.3f}")

    # =================================================================
    # TEST 6: Cross-race validation (Race 1 -> Race 2)
    # =================================================================
    print("\n" + "=" * 80)
    print("TEST 6: CROSS-RACE VALIDATION (Race 1 -> Race 2)")
    print("=" * 80)

    # Train on all of Race 1, test on Race 2
    predictions = predict_relative_performance(indy_r1, indy_r2)
    actuals = indy_r2['relative_time'].values
    positions = indy_r2['position'].values

    cross_rmse = np.sqrt(np.mean((actuals - predictions) ** 2))
    cross_mae = np.mean(np.abs(actuals - predictions))

    print(f"\nRace 1 -> Race 2 Results:")
    print(f"  RMSE: {cross_rmse:.3f}s")
    print(f"  MAE:  {cross_mae:.3f}s")

    # Position-stratified
    print("\nBy position group:")
    for p_min, p_max, label in [(1, 5, 'P1-5'), (6, 10, 'P6-10'), (11, 15, 'P11-15'), (16, 25, 'P16+')]:
        mask = (positions >= p_min) & (positions <= p_max)
        if mask.sum() > 0:
            rmse = np.sqrt(np.mean((actuals[mask] - predictions[mask]) ** 2))
            print(f"  {label}: RMSE = {rmse:.3f}s (n={mask.sum()})")

    # =================================================================
    # TEST 7: VIR validation (if available)
    # =================================================================
    if vir_data is not None:
        print("\n" + "=" * 80)
        print("TEST 7: VIR TRACK VALIDATION")
        print("=" * 80)

        # Within-race validation
        results_vir = expanding_window_validation(vir_data, min_train_laps=5)

        vir_rmse = np.sqrt((results_vir['error'] ** 2).mean())
        vir_mae = results_vir['abs_error'].mean()

        print(f"\nVIR Within-Race Results:")
        print(f"  RMSE: {vir_rmse:.3f}s")
        print(f"  MAE:  {vir_mae:.3f}s")

        # Cross-track validation (Indianapolis -> VIR)
        print("\nCross-track (Indianapolis Race 1 -> VIR):")
        predictions = predict_relative_performance(indy_r1, vir_data)
        actuals = vir_data['relative_time'].values

        cross_track_rmse = np.sqrt(np.mean((actuals - predictions) ** 2))
        print(f"  RMSE: {cross_track_rmse:.3f}s")

    # =================================================================
    # TEST 8: Alpha sensitivity analysis
    # =================================================================
    print("\n" + "-" * 80)
    print("TEST 8: ALPHA SENSITIVITY ANALYSIS")
    print("-" * 80)

    print("\nRMSE vs alpha (weight on prev_relative):")
    for alpha in [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]:
        results = expanding_window_validation(indy_r1, min_train_laps=5, alpha=alpha)
        rmse = np.sqrt((results['error'] ** 2).mean())
        print(f"  alpha = {alpha:.1f}: RMSE = {rmse:.3f}s")

    # =================================================================
    # SUMMARY
    # =================================================================
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    print(f"\nIndianapolis Race 1 (within-race):")
    print(f"  Overall RMSE: {overall_rmse:.3f}s")
    print(f"  Frontrunners (P1-5): {results_r1[results_r1['pos_group'] == 'P1-5']['error'].apply(lambda x: x**2).mean()**0.5:.3f}s")
    print(f"  Backmarkers (P16+): {results_r1[results_r1['pos_group'] == 'P16+']['error'].apply(lambda x: x**2).mean()**0.5:.3f}s")

    print(f"\nCross-race (Race 1 -> Race 2): RMSE = {cross_rmse:.3f}s")

    # Conclusions
    print("\n" + "-" * 80)
    print("CONCLUSIONS")
    print("-" * 80)

    if overall_rmse < 2.5:
        print("PASS: Within-race RMSE < 2.5s")
    else:
        print(f"FAIL: Within-race RMSE = {overall_rmse:.3f}s (target < 2.5s)")

    if cross_rmse < 4.0:
        print("PASS: Cross-race RMSE < 4.0s")
    else:
        print(f"FAIL: Cross-race RMSE = {cross_rmse:.3f}s (target < 4.0s)")


if __name__ == "__main__":
    main()
