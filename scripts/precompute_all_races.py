"""
Precompute features and validation results for all 14 races.

This script processes all races and saves:
1. Race features (positions, gaps, fighting status, etc.)
2. Validation results for different warmup/horizon combinations
3. Top-5 finish predictions from each lap
4. Per-driver prediction quality metrics

Output: data/processed/{track}/{race}_*.parquet
"""

import pandas as pd
import numpy as np
from pathlib import Path
import json
from typing import Dict, List, Tuple
from motorsport_modeling.models.feature_engineering import prepare_race_features

# Configuration
TRACKS = ['barber', 'cota', 'indianapolis', 'road-america', 'sebring', 'sonoma', 'vir']
RACES = ['race1', 'race2']
WARMUP_LAPS = [3, 5, 8, 10, 15]
PREDICTION_HORIZONS = [1, 2, 3, 5]  # laps ahead

BASE_DIR = Path(__file__).parent.parent
RAW_DATA_DIR = BASE_DIR / "data" / "raw" / "tracks"
PROCESSED_DIR = BASE_DIR / "data" / "processed"


def predict_relative_performance(
    train_data: pd.DataFrame,
    test_data: pd.DataFrame,
    alpha: float = 0.3
) -> np.ndarray:
    """Simple weighted average prediction of relative lap time."""
    driver_means = train_data.groupby('vehicle_number')['relative_time'].mean().to_dict()

    test = test_data.copy()
    test['driver_mean'] = test['vehicle_number'].map(driver_means).fillna(0)
    test['prev_relative'] = test['prev_relative'].fillna(test['driver_mean'])

    predictions = alpha * test['prev_relative'].values + (1 - alpha) * test['driver_mean'].values
    return predictions


def compute_validation_metrics(
    data: pd.DataFrame,
    warmup_laps: int,
    horizon: int
) -> pd.DataFrame:
    """
    Compute prediction vs actual for given warmup and horizon.

    Args:
        data: Race data with relative_time column
        warmup_laps: Number of laps to train on before making predictions
        horizon: How many laps ahead to predict (1=next lap, 2=2 laps ahead, etc.)

    Returns:
        DataFrame with columns: [prediction_lap, vehicle_number, actual, predicted, error, horizon]
    """
    max_lap = int(data['lap'].max())
    results = []

    for train_end in range(warmup_laps, max_lap - horizon + 1):
        predict_lap = train_end + horizon

        # Train on laps 1 to train_end
        train = data[data['lap'] <= train_end]

        # Test on predict_lap
        test = data[data['lap'] == predict_lap].copy()

        if len(test) == 0:
            continue

        # Make predictions
        predictions = predict_relative_performance(train, test)
        actuals = test['relative_time'].values
        positions = test['position'].values
        vehicles = test['vehicle_number'].values

        for i in range(len(predictions)):
            results.append({
                'prediction_lap': train_end,  # Lap we're standing at when making prediction
                'target_lap': predict_lap,
                'vehicle_number': vehicles[i],
                'position': positions[i],
                'actual': actuals[i],
                'predicted': predictions[i],
                'error': actuals[i] - predictions[i],
                'abs_error': abs(actuals[i] - predictions[i]),
                'warmup_laps': warmup_laps,
                'horizon': horizon
            })

    return pd.DataFrame(results)


def compute_ndcg_at_k(actual_ranking: List, predicted_ranking: List, k: int = 5) -> float:
    """
    Compute NDCG@k (Normalized Discounted Cumulative Gain).

    Penalizes incorrect ordering - if we predict drivers in wrong order, we get lower score.

    Args:
        actual_ranking: List of vehicle numbers in actual finish order [1st, 2nd, 3rd, ...]
        predicted_ranking: List of vehicle numbers in predicted order [1st, 2nd, 3rd, ...]
        k: Number of positions to consider (default 5 for top-5)

    Returns:
        NDCG score between 0 and 1 (1 = perfect ranking, 0 = worst)
    """
    # Create relevance scores: position 1 gets score 5, position 2 gets 4, etc.
    actual_relevance = {driver: k - i for i, driver in enumerate(actual_ranking[:k])}

    # DCG: Discounted Cumulative Gain for our prediction
    dcg = 0.0
    for i, driver in enumerate(predicted_ranking[:k]):
        relevance = actual_relevance.get(driver, 0)  # 0 if driver not in actual top-k
        dcg += relevance / np.log2(i + 2)  # i+2 because positions are 1-indexed

    # IDCG: Ideal DCG (if we predicted perfectly)
    idcg = 0.0
    for i in range(min(k, len(actual_ranking))):
        relevance = k - i
        idcg += relevance / np.log2(i + 2)

    # NDCG: Normalize
    if idcg == 0:
        return 0.0
    return dcg / idcg


def predict_top5_finish(
    data: pd.DataFrame,
    prediction_lap: int
) -> Dict:
    """
    From a given lap, predict final top-5 finishers.

    Strategy: Use current position + predicted relative time to estimate final order.

    Computes both:
    - Set-based accuracy: How many of top-5 drivers did we identify? (ignores order)
    - NDCG@5: How well did we rank them? (penalizes incorrect ordering)
    """
    # Get actual final positions
    final_lap = int(data['lap'].max())
    final_positions = data[data['lap'] == final_lap][['vehicle_number', 'position']].copy()
    final_positions = final_positions.rename(columns={'position': 'final_position'})
    actual_top5 = final_positions.nsmallest(5, 'final_position')['vehicle_number'].tolist()

    # Make prediction from prediction_lap
    if prediction_lap >= final_lap:
        return None

    # Train on laps 1 to prediction_lap
    train = data[data['lap'] <= prediction_lap]
    test = data[data['lap'] == final_lap].copy()

    if len(test) == 0:
        return None

    # Predict final relative times
    predictions = predict_relative_performance(train, test)

    # Estimate final positions based on predicted relative times
    test['predicted_relative'] = predictions
    test['predicted_position'] = test['predicted_relative'].rank(method='first')
    predicted_top5 = test.nsmallest(5, 'predicted_position')['vehicle_number'].tolist()

    # Compute set-based accuracy (ignores order)
    correct_count = len(set(predicted_top5) & set(actual_top5))

    # Compute NDCG@5 (penalizes incorrect ordering)
    ndcg = compute_ndcg_at_k(actual_top5, predicted_top5, k=5)

    return {
        'prediction_lap': prediction_lap,
        'actual_top5': actual_top5,
        'predicted_top5': predicted_top5,
        'correct_count': correct_count,
        'set_accuracy': correct_count / 5.0,  # Renamed from 'accuracy'
        'ndcg': ndcg  # New metric
    }


def process_race(track: str, race: str) -> Dict:
    """Process a single race and compute all validation metrics."""
    print(f"\n{'='*70}")
    print(f"Processing {track} / {race}")
    print('='*70)

    race_dir = RAW_DATA_DIR / track / race

    # Check if race data exists
    lap_time_files = list(race_dir.glob("*lap_time*.csv"))
    if not lap_time_files:
        print(f"  ⚠️  No lap time data found, skipping")
        return None

    # Load race features
    print(f"  Loading race features...")
    try:
        # Find endurance file if it exists
        endurance_files = list(race_dir.glob("*AnalysisEndurance*.CSV"))
        endurance_file = endurance_files[0] if endurance_files else None

        # Estimate total laps (will be corrected by prepare_race_features)
        data = prepare_race_features(
            lap_time_file=lap_time_files[0],
            total_laps=30,  # Will auto-detect
            endurance_file=endurance_file,
            verbose=False
        )

        # Filter valid data
        data = data[data['lap_time'].notna()].copy()
        if 'is_under_yellow' in data.columns:
            data = data[data['is_under_yellow'] == 0].copy()

        # Compute relative time
        field_median = data.groupby('lap')['lap_time'].median()
        data['field_median'] = data['lap'].map(field_median)
        data['relative_time'] = data['lap_time'] - data['field_median']

        # Filter outliers
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

        print(f"  Loaded {len(data)} rows, {data['lap'].nunique()} laps, {data['vehicle_number'].nunique()} drivers")

    except Exception as e:
        print(f"  ❌ Error loading data: {e}")
        return None

    # Save race features
    output_dir = PROCESSED_DIR / track
    output_dir.mkdir(parents=True, exist_ok=True)

    features_file = output_dir / f"{race}_features.parquet"
    data.to_parquet(features_file, index=False)
    print(f"  ✓ Saved features: {features_file}")

    # Compute validation metrics for all warmup/horizon combinations
    print(f"  Computing validation metrics...")
    all_validation = []

    for warmup in WARMUP_LAPS:
        for horizon in PREDICTION_HORIZONS:
            validation = compute_validation_metrics(data, warmup, horizon)
            if len(validation) > 0:
                all_validation.append(validation)
                print(f"    Warmup={warmup}, Horizon={horizon}: {len(validation)} predictions")

    if all_validation:
        validation_df = pd.concat(all_validation, ignore_index=True)
        validation_file = output_dir / f"{race}_validation.parquet"
        validation_df.to_parquet(validation_file, index=False)
        print(f"  ✓ Saved validation: {validation_file}")

    # Compute top-5 finish predictions
    print(f"  Computing top-5 predictions...")
    top5_results = []
    max_lap = int(data['lap'].max())

    # Predict from laps: sample every 2-3 laps for better granularity
    for pred_lap in range(WARMUP_LAPS[0] + 1, max_lap - 2, 3):
        result = predict_top5_finish(data, pred_lap)
        if result:
            top5_results.append(result)
            print(f"    Lap {pred_lap}: Set={result['set_accuracy']:.1%}, NDCG={result['ndcg']:.3f}")

    if top5_results:
        top5_df = pd.DataFrame(top5_results)
        top5_file = output_dir / f"{race}_top5.parquet"
        top5_df.to_parquet(top5_file, index=False)
        print(f"  ✓ Saved top-5 predictions: {top5_file}")

    # Compute per-driver summary
    print(f"  Computing per-driver metrics...")
    driver_stats = validation_df.groupby('vehicle_number').agg({
        'error': lambda x: np.sqrt((x ** 2).mean()),  # RMSE
        'abs_error': 'mean',  # MAE
        'position': 'mean',
        'prediction_lap': 'count'
    }).rename(columns={
        'error': 'rmse',
        'abs_error': 'mae',
        'position': 'avg_position',
        'prediction_lap': 'num_predictions'
    })

    # Find worst lap for each driver
    worst_laps = validation_df.loc[validation_df.groupby('vehicle_number')['abs_error'].idxmax()]
    worst_laps = worst_laps[['vehicle_number', 'target_lap', 'abs_error']].rename(columns={
        'target_lap': 'worst_lap',
        'abs_error': 'worst_error'
    })

    driver_stats = driver_stats.merge(worst_laps, on='vehicle_number', how='left')
    driver_stats = driver_stats.sort_values('rmse')  # Sort by accuracy (best first)

    driver_file = output_dir / f"{race}_driver_stats.parquet"
    driver_stats.to_parquet(driver_file)
    print(f"  ✓ Saved driver stats: {driver_file}")

    # Create metadata
    metadata = {
        'track': track,
        'race': race,
        'total_laps': int(max_lap),
        'num_drivers': int(data['vehicle_number'].nunique()),
        'num_samples': len(data),
        'warmup_laps': WARMUP_LAPS,
        'prediction_horizons': PREDICTION_HORIZONS,
        'files': {
            'features': str(features_file.name),
            'validation': str(validation_file.name) if all_validation else None,
            'top5': str(top5_file.name) if top5_results else None,
            'driver_stats': str(driver_file.name)
        }
    }

    metadata_file = output_dir / f"{race}_metadata.json"
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    print(f"  ✓ Saved metadata: {metadata_file}")

    return metadata


def main():
    print("="*70)
    print("PRECOMPUTING ALL RACE DATA")
    print("="*70)
    print(f"Tracks: {', '.join(TRACKS)}")
    print(f"Races per track: {', '.join(RACES)}")
    print(f"Warmup laps: {WARMUP_LAPS}")
    print(f"Prediction horizons: {PREDICTION_HORIZONS}")
    print(f"Total combinations: {len(WARMUP_LAPS) * len(PREDICTION_HORIZONS)}")

    # Create output directory
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    # Process all races
    manifest = {}
    success_count = 0
    fail_count = 0

    for track in TRACKS:
        manifest[track] = {}
        for race in RACES:
            metadata = process_race(track, race)
            if metadata:
                manifest[track][race] = metadata
                success_count += 1
            else:
                manifest[track][race] = None
                fail_count += 1

    # Save manifest
    manifest_file = PROCESSED_DIR / "manifest.json"
    with open(manifest_file, 'w') as f:
        json.dump(manifest, f, indent=2)

    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(f"Successfully processed: {success_count} races")
    print(f"Failed: {fail_count} races")
    print(f"Manifest saved: {manifest_file}")
    print("\nProcessed data location:")
    print(f"  {PROCESSED_DIR}")


if __name__ == "__main__":
    main()
