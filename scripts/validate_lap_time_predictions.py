"""
Validate lap time prediction model with proper temporal ordering.

Two validation strategies:
1. One-step-ahead (expanding window): Train 1-N, predict N+1, expand, repeat
2. Multi-step-ahead: Train 1-N, predict N+k for various horizons k

No data leakage - only past data used for predictions.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from scipy import stats
from typing import List, Dict, Tuple

from motorsport_modeling.models.feature_engineering import prepare_race_features
from motorsport_modeling.models.lap_time_predictor import BaselineLapPredictor


def expanding_window_validation(
    data: pd.DataFrame,
    min_train_laps: int = 5,
    verbose: bool = True
) -> Dict:
    """
    One-step-ahead validation with expanding window.

    Train on laps 1-N, predict N+1, then train on 1-(N+1), predict N+2, etc.

    Parameters
    ----------
    data : pd.DataFrame
        Race data with lap_time, vehicle_number, lap, position, laps_remaining
    min_train_laps : int
        Minimum laps to use for initial training
    verbose : bool
        Print progress

    Returns
    -------
    dict
        Results with per-lap predictions and overall RMSE
    """
    max_lap = int(data['lap'].max())

    all_predictions = []
    all_actuals = []
    per_lap_rmse = []

    if verbose:
        print(f"\nExpanding window: train from lap {min_train_laps}, predict one-step-ahead")

    for train_end in range(min_train_laps, max_lap):
        predict_lap = train_end + 1

        # Train on laps 1 to train_end
        train_data = data[data['lap'] <= train_end].copy()
        test_data = data[data['lap'] == predict_lap].copy()

        if len(test_data) == 0:
            continue

        # Fit model
        model = BaselineLapPredictor()
        model.fit(train_data, verbose=False)

        # Predict
        predictions = model.predict(test_data)
        actuals = test_data['lap_time'].values

        # Store results
        all_predictions.extend(predictions)
        all_actuals.extend(actuals)

        # Per-lap RMSE
        lap_rmse = np.sqrt(np.mean((actuals - predictions) ** 2))
        per_lap_rmse.append({
            'train_end': train_end,
            'predict_lap': predict_lap,
            'rmse': lap_rmse,
            'n_samples': len(test_data)
        })

        if verbose and predict_lap % 5 == 0:
            print(f"  Train 1-{train_end}, predict lap {predict_lap}: RMSE = {lap_rmse:.3f}s")

    # Overall metrics
    all_predictions = np.array(all_predictions)
    all_actuals = np.array(all_actuals)
    residuals = all_actuals - all_predictions

    overall_rmse = np.sqrt(np.mean(residuals ** 2))
    overall_mae = np.mean(np.abs(residuals))

    if verbose:
        print(f"\n  Overall one-step-ahead RMSE: {overall_rmse:.3f}s")
        print(f"  Overall one-step-ahead MAE: {overall_mae:.3f}s")

    return {
        'rmse': overall_rmse,
        'mae': overall_mae,
        'per_lap_rmse': per_lap_rmse,
        'predictions': all_predictions,
        'actuals': all_actuals
    }


def multi_step_validation(
    data: pd.DataFrame,
    train_end: int,
    horizons: List[int] = [1, 3, 5, 10],
    verbose: bool = True
) -> Dict:
    """
    Multi-step-ahead validation from a fixed training window.

    Train on laps 1-N, predict N+k for various horizons k.

    Parameters
    ----------
    data : pd.DataFrame
        Race data
    train_end : int
        Last lap to include in training
    horizons : list of int
        Prediction horizons to evaluate (k values)
    verbose : bool
        Print progress

    Returns
    -------
    dict
        Results with RMSE for each horizon
    """
    max_lap = int(data['lap'].max())

    # Train model
    train_data = data[data['lap'] <= train_end].copy()
    model = BaselineLapPredictor()
    model.fit(train_data, verbose=False)

    if verbose:
        print(f"\nMulti-step validation: trained on laps 1-{train_end}")

    horizon_results = []

    for k in horizons:
        predict_lap = train_end + k

        if predict_lap > max_lap:
            continue

        test_data = data[data['lap'] == predict_lap].copy()

        if len(test_data) == 0:
            continue

        predictions = model.predict(test_data)
        actuals = test_data['lap_time'].values

        rmse = np.sqrt(np.mean((actuals - predictions) ** 2))
        mae = np.mean(np.abs(actuals - predictions))

        horizon_results.append({
            'horizon': k,
            'predict_lap': predict_lap,
            'rmse': rmse,
            'mae': mae,
            'n_samples': len(test_data)
        })

        if verbose:
            print(f"  Horizon k={k} (lap {predict_lap}): RMSE = {rmse:.3f}s")

    return {
        'train_end': train_end,
        'horizon_results': horizon_results
    }


def cross_race_validation(
    train_data: pd.DataFrame,
    test_data: pd.DataFrame,
    verbose: bool = True
) -> Dict:
    """
    Cross-race validation: train on one race, test on another.

    Parameters
    ----------
    train_data : pd.DataFrame
        Training race data
    test_data : pd.DataFrame
        Test race data

    Returns
    -------
    dict
        Results with RMSE and per-driver breakdown
    """
    # Train on full training race
    model = BaselineLapPredictor()
    model.fit(train_data, verbose=verbose)

    # Evaluate on test race
    results = model.evaluate(test_data, verbose=verbose)

    # Per-driver analysis
    test_data = test_data.copy()
    test_data['predicted'] = model.predict(test_data)
    test_data['residual'] = test_data['lap_time'] - test_data['predicted']

    driver_rmse = test_data.groupby('vehicle_number').apply(
        lambda x: np.sqrt((x['residual'] ** 2).mean())
    ).sort_values()

    results['driver_rmse'] = driver_rmse

    return results


def filter_clean_laps(data: pd.DataFrame, verbose: bool = True) -> pd.DataFrame:
    """
    Filter out yellow flag laps and outlier lap times.

    These create huge noise in predictions and should be excluded.
    """
    original_count = len(data)

    # Filter yellow flag laps if column exists
    if 'is_under_yellow' in data.columns:
        data = data[data['is_under_yellow'] == 0].copy()
        yellow_removed = original_count - len(data)
        if verbose and yellow_removed > 0:
            print(f"  Removed {yellow_removed} yellow flag laps")

    # Filter statistical outliers (> 3 std from mean per driver)
    def filter_outliers(group):
        mean = group['lap_time'].mean()
        std = group['lap_time'].std()
        if std > 0:
            return group[abs(group['lap_time'] - mean) <= 3 * std]
        return group

    before_outlier = len(data)
    data = data.groupby('vehicle_number', group_keys=False).apply(filter_outliers)
    outliers_removed = before_outlier - len(data)
    if verbose and outliers_removed > 0:
        print(f"  Removed {outliers_removed} outlier laps (>3 std)")

    if verbose:
        print(f"  Clean samples: {len(data)} (removed {original_count - len(data)} total)")

    return data


def main():
    print("=" * 70)
    print("LAP TIME PREDICTION VALIDATION")
    print("Expanding window + Multi-step horizons")
    print("=" * 70)

    # Paths
    base_dir = Path(__file__).parent.parent / "data" / "raw" / "tracks" / "indianapolis"
    race1_dir = base_dir / "race1"
    race2_dir = base_dir / "race2"

    total_laps = 26

    # =================================================================
    # Load Race 1 Data
    # =================================================================
    print("\n" + "=" * 70)
    print("Loading Race 1 Data")
    print("=" * 70)

    race1_lap_file = race1_dir / "R1_indianapolis_motor_speedway_lap_time.csv"
    race1_weather_file = race1_dir / "26_Weather_Race 1.CSV"
    race1_endurance_file = race1_dir / "23_AnalysisEnduranceWithSections_Race 1.CSV"

    race1_data = prepare_race_features(
        lap_time_file=race1_lap_file,
        total_laps=total_laps,
        weather_file=race1_weather_file if race1_weather_file.exists() else None,
        endurance_file=race1_endurance_file if race1_endurance_file.exists() else None,
        verbose=True
    )

    race1_data = race1_data[race1_data['lap_time'].notna()].copy()
    print(f"\nRace 1 raw samples: {len(race1_data)}")

    # Filter clean laps
    print("\nFiltering clean laps (removing yellow flags and outliers):")
    race1_data = filter_clean_laps(race1_data, verbose=True)

    # =================================================================
    # Test 1: Expanding Window (One-Step-Ahead)
    # =================================================================
    print("\n" + "=" * 70)
    print("TEST 1: EXPANDING WINDOW VALIDATION")
    print("Train 1-N, predict N+1, expand window, repeat")
    print("=" * 70)

    expanding_results = expanding_window_validation(
        race1_data,
        min_train_laps=5,
        verbose=True
    )

    # =================================================================
    # Test 2: Multi-Step Horizons
    # =================================================================
    print("\n" + "=" * 70)
    print("TEST 2: MULTI-STEP HORIZON VALIDATION")
    print("Train on fixed window, predict at various horizons")
    print("=" * 70)

    # Test from different training windows
    for train_end in [10, 15]:
        multi_results = multi_step_validation(
            race1_data,
            train_end=train_end,
            horizons=[1, 2, 3, 5, 8, 10],
            verbose=True
        )

    # =================================================================
    # Test 3: Cross-Race Validation
    # =================================================================
    print("\n" + "=" * 70)
    print("TEST 3: CROSS-RACE VALIDATION")
    print("Train on Race 1, test on Race 2")
    print("=" * 70)

    # Load Race 2
    race2_lap_file = race2_dir / "R2_indianapolis_motor_speedway_lap_time.csv"
    race2_weather_file = race2_dir / "26_Weather_Race 2.CSV"
    race2_endurance_file = race2_dir / "23_AnalysisEnduranceWithSections_Race 2.CSV"

    race2_data = prepare_race_features(
        lap_time_file=race2_lap_file,
        total_laps=total_laps,
        weather_file=race2_weather_file if race2_weather_file.exists() else None,
        endurance_file=race2_endurance_file if race2_endurance_file.exists() else None,
        verbose=True
    )

    race2_data = race2_data[race2_data['lap_time'].notna()].copy()
    print(f"\nRace 2 raw samples: {len(race2_data)}")

    # Filter clean laps
    print("\nFiltering clean laps (removing yellow flags and outliers):")
    race2_data = filter_clean_laps(race2_data, verbose=True)

    print("\n--- Cross-Race Results ---")
    cross_results = cross_race_validation(race1_data, race2_data, verbose=True)

    # =================================================================
    # Summary
    # =================================================================
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    print("\n--- RMSE by Validation Strategy ---")
    print(f"{'Strategy':<40} {'RMSE':<10}")
    print("-" * 50)
    print(f"{'Expanding window (one-step-ahead)':<40} {expanding_results['rmse']:.3f}s")
    print(f"{'Cross-race (Race 1 -> Race 2)':<40} {cross_results['rmse']:.3f}s")

    # Success criteria
    print("\n--- SUCCESS CRITERIA ---")

    one_step_pass = expanding_results['rmse'] < 1.0
    cross_race_pass = cross_results['rmse'] < 1.5

    print(f"One-step-ahead RMSE < 1.0s: {'PASS' if one_step_pass else 'FAIL'} ({expanding_results['rmse']:.3f}s)")
    print(f"Cross-race RMSE < 1.5s: {'PASS' if cross_race_pass else 'FAIL'} ({cross_results['rmse']:.3f}s)")

    # Tier assessment
    if cross_results['rmse'] < 0.8:
        tier = "EXCELLENT"
    elif cross_results['rmse'] < 1.2:
        tier = "GOOD"
    elif cross_results['rmse'] < 1.5:
        tier = "ACCEPTABLE"
    else:
        tier = "REWORK NEEDED"

    print(f"\nOverall Tier: {tier}")

    print("\n" + "=" * 70)
    print("VALIDATION COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
