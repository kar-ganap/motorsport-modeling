"""
Validate technique metrics on VIR track.

This script runs the same validation as validate_metrics_properly.py
but on VIR data to confirm metrics generalize across tracks.

Key Tests:
1. Within-driver correlation: metric change -> lap time change
2. Cross-driver correlation: metric rank -> pace rank
3. Variance structure: profile vs state features
"""

import pandas as pd
import numpy as np
from pathlib import Path
from scipy import stats

from motorsport_modeling.data.telemetry_loader import load_telemetry, load_lap_times
from motorsport_modeling.metrics.tier1_metrics import (
    compute_coasting_pct,
    compute_braking_smoothness,
    compute_g_force_utilization,
    compute_throttle_timing
)


def compute_all_metrics(telemetry, vehicle_number, lap):
    """Compute all metrics for a vehicle-lap pair."""
    try:
        coasting = compute_coasting_pct(telemetry, vehicle_number, lap)
        braking = compute_braking_smoothness(telemetry, vehicle_number, lap)
        g_force = compute_g_force_utilization(telemetry, vehicle_number, lap)
        throttle = compute_throttle_timing(telemetry, vehicle_number, lap)

        return {
            'coasting_pct': coasting['coasting_pct'],
            'brake_cv': braking.get('peak_brake_cv', np.nan),
            'mean_combined_g': g_force['mean_combined_g'],
            'lift_off_count': throttle.get('lift_off_count', np.nan),
            'full_throttle_pct': throttle.get('full_throttle_pct', np.nan),
        }
    except Exception as e:
        return None


def main():
    print("=" * 70)
    print("METRICS VALIDATION ON VIR")
    print("Confirming metrics generalize beyond Indianapolis")
    print("=" * 70)

    # Path to VIR data
    data_dir = Path(__file__).parent.parent / "data" / "raw" / "tracks" / "vir" / "race1"

    # Load data
    print("\n--- Loading VIR Race 1 Data ---")

    # Get available laps
    lap_time_file = data_dir / "vir_lap_time_R1.csv"
    if not lap_time_file.exists():
        print(f"ERROR: Lap time file not found: {lap_time_file}")
        return

    lap_times = load_lap_times(data_dir)
    max_lap = int(lap_times['lap'].max())
    print(f"Max lap in data: {max_lap}")

    # Load telemetry
    telemetry = load_telemetry(
        data_dir,
        laps=list(range(1, min(max_lap + 1, 21))),  # Cap at 20 laps for speed
        pivot_to_wide=True,
        verbose=True
    )

    print(f"Telemetry shape: {telemetry.shape}")
    print(f"Vehicles: {sorted(telemetry['vehicle_number'].unique())}")

    # =================================================================
    # Compute per-lap metrics
    # =================================================================
    print("\n--- Computing Per-Lap Metrics ---")

    per_lap_data = []

    vehicles = sorted(telemetry['vehicle_number'].unique())
    for veh in vehicles:
        veh_laps = sorted(telemetry[telemetry['vehicle_number'] == veh]['lap'].unique())

        for lap in veh_laps:
            # Get lap time
            lt_row = lap_times[
                (lap_times['vehicle_number'] == veh) &
                (lap_times['lap'] == lap)
            ]

            if len(lt_row) == 0 or pd.isna(lt_row['lap_time'].iloc[0]):
                continue

            lap_time = lt_row['lap_time'].iloc[0]

            # Compute metrics
            metrics = compute_all_metrics(telemetry, veh, lap)
            if metrics is None:
                continue

            per_lap_data.append({
                'vehicle_number': veh,
                'lap': lap,
                'lap_time': lap_time,
                **metrics
            })

    df = pd.DataFrame(per_lap_data)
    print(f"Computed metrics for {len(df)} vehicle-lap pairs")
    print(f"Vehicles with data: {df['vehicle_number'].nunique()}")

    # =================================================================
    # Test 1: Within-Driver Correlations
    # =================================================================
    print("\n" + "=" * 70)
    print("TEST 1: WITHIN-DRIVER CORRELATIONS")
    print("Does metric change predict lap time change for the same driver?")
    print("=" * 70)

    metric_cols = ['coasting_pct', 'brake_cv', 'mean_combined_g',
                   'lift_off_count', 'full_throttle_pct']

    expected_signs = {
        'coasting_pct': 'positive',     # More coasting -> slower
        'brake_cv': 'positive',         # More inconsistent -> slower
        'mean_combined_g': 'negative',  # Higher G -> faster
        'lift_off_count': 'positive',   # More lift-offs -> slower
        'full_throttle_pct': 'negative' # More WOT -> faster
    }

    within_results = {}

    for metric in metric_cols:
        # Collect all within-driver correlations
        correlations = []

        for veh in df['vehicle_number'].unique():
            veh_data = df[df['vehicle_number'] == veh].dropna(subset=[metric, 'lap_time'])

            if len(veh_data) >= 5:  # Need enough points
                r, p = stats.pearsonr(veh_data[metric], veh_data['lap_time'])
                correlations.append(r)

        if correlations:
            mean_r = np.mean(correlations)
            expected = expected_signs[metric]
            actual = 'positive' if mean_r > 0 else 'negative'
            status = "OK" if expected == actual else "WRONG"

            within_results[metric] = {
                'mean_r': mean_r,
                'expected': expected,
                'actual': actual,
                'status': status,
                'n_drivers': len(correlations)
            }

            print(f"\n{metric}:")
            print(f"  Mean r = {mean_r:.3f} (n={len(correlations)} drivers)")
            print(f"  Expected: {expected}, Actual: {actual}")
            print(f"  Status: {status}")

    # =================================================================
    # Test 2: Cross-Driver Correlations
    # =================================================================
    print("\n" + "=" * 70)
    print("TEST 2: CROSS-DRIVER CORRELATIONS")
    print("Does metric ranking predict pace ranking across drivers?")
    print("=" * 70)

    # Compute driver-level means
    driver_means = df.groupby('vehicle_number').agg({
        'lap_time': 'mean',
        'coasting_pct': 'mean',
        'brake_cv': 'mean',
        'mean_combined_g': 'mean',
        'lift_off_count': 'mean',
        'full_throttle_pct': 'mean'
    }).reset_index()

    cross_results = {}

    for metric in metric_cols:
        valid_data = driver_means.dropna(subset=[metric, 'lap_time'])

        if len(valid_data) >= 5:
            rho, p = stats.spearmanr(valid_data[metric], valid_data['lap_time'])

            cross_results[metric] = {
                'rho': rho,
                'p_value': p,
                'significant': p < 0.05,
                'n_drivers': len(valid_data)
            }

            sig = "*" if p < 0.05 else ""
            print(f"\n{metric}:")
            print(f"  Spearman rho = {rho:.3f}{sig} (p={p:.3f})")
            print(f"  n = {len(valid_data)} drivers")

    # =================================================================
    # Test 3: Variance Structure
    # =================================================================
    print("\n" + "=" * 70)
    print("TEST 3: VARIANCE STRUCTURE (Profile vs State)")
    print("High ratio = profile feature; Low ratio = state feature")
    print("=" * 70)

    variance_results = {}

    for metric in metric_cols:
        # Within-driver std (average)
        within_std = df.groupby('vehicle_number')[metric].std().mean()

        # Cross-driver std
        driver_means_metric = df.groupby('vehicle_number')[metric].mean()
        cross_std = driver_means_metric.std()

        ratio = cross_std / within_std if within_std > 0 else np.nan

        if ratio > 1.5:
            feature_type = "PROFILE"
        elif ratio < 0.7:
            feature_type = "STATE"
        else:
            feature_type = "MIXED"

        variance_results[metric] = {
            'within_std': within_std,
            'cross_std': cross_std,
            'ratio': ratio,
            'type': feature_type
        }

        print(f"\n{metric}:")
        print(f"  Within-driver std: {within_std:.3f}")
        print(f"  Cross-driver std:  {cross_std:.3f}")
        print(f"  Ratio: {ratio:.2f} -> {feature_type}")

    # =================================================================
    # Summary
    # =================================================================
    print("\n" + "=" * 70)
    print("SUMMARY: VIR VALIDATION RESULTS")
    print("=" * 70)

    # Within-driver results
    within_ok = sum(1 for v in within_results.values() if v['status'] == 'OK')
    print(f"\nWithin-driver correlations: {within_ok}/{len(within_results)} correct direction")

    # Cross-driver results
    cross_sig = sum(1 for v in cross_results.values() if v['significant'])
    print(f"Cross-driver correlations: {cross_sig}/{len(cross_results)} significant (p<0.05)")

    # Feature types
    print("\nFeature Classification:")
    for metric, result in variance_results.items():
        print(f"  {metric}: {result['type']} (ratio={result['ratio']:.2f})")

    # Overall assessment
    print("\n" + "-" * 70)
    if within_ok >= 3 and cross_sig >= 2:
        print("PASS: Metrics generalize to VIR")
    elif within_ok >= 2 and cross_sig >= 1:
        print("PARTIAL: Some metrics work on VIR")
    else:
        print("FAIL: Metrics do not generalize - need investigation")

    return {
        'within_results': within_results,
        'cross_results': cross_results,
        'variance_results': variance_results
    }


if __name__ == "__main__":
    main()
