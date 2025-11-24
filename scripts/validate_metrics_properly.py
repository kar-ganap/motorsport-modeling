"""
Proper validation of Tier 1 metrics.

Tests:
1. Within-driver correlation: Does metric change predict lap time change?
2. Cross-driver correlation: Does metric ranking predict pace ranking?
3. Predictive power: Do metrics improve lap time prediction?

Usage:
    uv run python scripts/validate_metrics_properly.py
"""

from pathlib import Path
import pandas as pd
import numpy as np
from scipy import stats

from motorsport_modeling.data.telemetry_loader import load_telemetry, load_lap_times
from motorsport_modeling.metrics.tier1_metrics import (
    compute_coasting_pct,
    compute_braking_smoothness,
    compute_g_force_utilization,
    compute_throttle_timing
)


def main():
    data_dir = Path(__file__).parent.parent / 'data' / 'raw' / 'tracks'

    track = 'indianapolis'
    race = 'race1'
    race_dir = data_dir / track / race

    print("="*70)
    print("PROPER VALIDATION OF TIER 1 METRICS")
    print("="*70)

    # Load data
    print("\nLoading data...")
    telemetry = load_telemetry(
        race_dir,
        laps=list(range(1, 21)),
        pivot_to_wide=True,
        verbose=False
    )

    lap_times = load_lap_times(race_dir)

    print(f"Telemetry: {len(telemetry)} rows")
    print(f"Lap times: {len(lap_times)} records")

    # =========================================================================
    # TEST 1: Within-driver correlation
    # =========================================================================
    print("\n" + "="*70)
    print("TEST 1: WITHIN-DRIVER CORRELATION")
    print("Does metric change predict lap time change for each driver?")
    print("="*70)

    # Compute per-lap metrics for all drivers
    per_lap_metrics = []

    for veh in telemetry['vehicle_number'].unique():
        veh_laps = telemetry[telemetry['vehicle_number'] == veh]['lap'].unique()

        for lap in veh_laps:
            # Get lap time
            lt = lap_times[(lap_times['vehicle_number'] == veh) & (lap_times['lap'] == lap)]
            if len(lt) == 0 or pd.isna(lt['lap_time'].iloc[0]):
                continue

            lap_time = lt['lap_time'].iloc[0]

            # Compute metrics for this lap
            coasting = compute_coasting_pct(telemetry, veh, lap)
            braking = compute_braking_smoothness(telemetry, veh, lap)
            g_force = compute_g_force_utilization(telemetry, veh, lap)
            throttle = compute_throttle_timing(telemetry, veh, lap)

            per_lap_metrics.append({
                'vehicle_number': veh,
                'lap': lap,
                'lap_time': lap_time,
                'coasting_pct': coasting['coasting_pct'],
                'brake_cv': braking.get('peak_brake_cv', braking.get('oscillations_per_event')),
                'mean_g': g_force['mean_combined_g'],
                'lift_off_count': throttle.get('lift_off_count', np.nan),
                'full_throttle_pct': throttle.get('full_throttle_pct', np.nan),
                'throttle_efficiency': throttle.get('throttle_efficiency', np.nan)
            })

    metrics_df = pd.DataFrame(per_lap_metrics)
    print(f"\nComputed metrics for {len(metrics_df)} driver-lap combinations")

    # Compute within-driver correlations
    metrics_to_test = ['coasting_pct', 'brake_cv', 'mean_g', 'lift_off_count', 'full_throttle_pct', 'throttle_efficiency']
    expected_direction = {
        'coasting_pct': 'positive',    # More coasting -> slower (worse)
        'brake_cv': 'positive',        # Higher CV (inconsistent) -> slower
        'mean_g': 'negative',          # More G -> faster (better)
        'lift_off_count': 'positive',  # More lift-offs -> slower (wheelspin)
        'full_throttle_pct': 'negative',  # More full throttle -> faster
        'throttle_efficiency': 'negative'  # Higher efficiency -> faster
    }

    print("\nWithin-driver correlations (metric vs lap_time):")
    print("Positive = metric increase -> slower lap (bad)")
    print("Negative = metric increase -> faster lap (good)")

    within_driver_corrs = {}

    for metric in metrics_to_test:
        # Calculate correlation for each driver, then average
        driver_corrs = []

        for veh in metrics_df['vehicle_number'].unique():
            veh_data = metrics_df[metrics_df['vehicle_number'] == veh]

            if len(veh_data) < 5:  # Need enough data points
                continue

            x = veh_data[metric].dropna()
            y = veh_data.loc[x.index, 'lap_time']

            if len(x) < 5:
                continue

            corr, p_value = stats.pearsonr(x, y)
            driver_corrs.append(corr)

        if len(driver_corrs) > 0:
            mean_corr = np.mean(driver_corrs)
            std_corr = np.std(driver_corrs)
            n_drivers = len(driver_corrs)

            expected = expected_direction[metric]
            matches = (mean_corr > 0 and expected == 'positive') or \
                      (mean_corr < 0 and expected == 'negative')

            status = "OK" if matches else "WRONG"

            print(f"\n  {metric}:")
            print(f"    Mean corr: {mean_corr:.3f} (±{std_corr:.3f})")
            print(f"    Expected: {expected}, Got: {'positive' if mean_corr > 0 else 'negative'}")
            print(f"    Status: {status}")
            print(f"    N drivers: {n_drivers}")

            within_driver_corrs[metric] = mean_corr

    # =========================================================================
    # TEST 2: Cross-driver correlation (rankings)
    # =========================================================================
    print("\n" + "="*70)
    print("TEST 2: CROSS-DRIVER CORRELATION")
    print("Does metric ranking predict pace ranking?")
    print("="*70)

    # Average metrics per driver
    driver_avg = metrics_df.groupby('vehicle_number').agg({
        'lap_time': 'mean',
        'coasting_pct': 'mean',
        'brake_cv': 'mean',
        'mean_g': 'mean',
        'lift_off_count': 'mean',
        'full_throttle_pct': 'mean',
        'throttle_efficiency': 'mean'
    }).dropna()

    print(f"\n{len(driver_avg)} drivers with complete data")

    print("\nSpearman rank correlations (metric rank vs lap time rank):")

    for metric in metrics_to_test:
        if metric not in driver_avg.columns:
            continue

        # For G-force, higher is better (faster), so we need to flip the sign
        if metric == 'mean_g':
            metric_values = -driver_avg[metric]  # Negate so lower rank = better
        else:
            metric_values = driver_avg[metric]

        corr, p_value = stats.spearmanr(metric_values, driver_avg['lap_time'])

        sig = "*" if p_value < 0.05 else ""
        print(f"  {metric}: rho={corr:.3f} (p={p_value:.3f}){sig}")

    # =========================================================================
    # TEST 3: Show actual rankings
    # =========================================================================
    print("\n" + "="*70)
    print("TEST 3: ACTUAL RANKINGS")
    print("="*70)

    # Rank drivers by pace
    driver_avg['pace_rank'] = driver_avg['lap_time'].rank()

    # Rank by each metric (lower is better for most)
    driver_avg['coasting_rank'] = driver_avg['coasting_pct'].rank()
    driver_avg['brake_rank'] = driver_avg['brake_cv'].rank()
    driver_avg['g_rank'] = (-driver_avg['mean_g']).rank()  # Higher G = better = lower rank
    driver_avg['liftoff_rank'] = driver_avg['lift_off_count'].rank()
    driver_avg['fullthrottle_rank'] = (-driver_avg['full_throttle_pct']).rank()  # Higher = better

    # Show top 5 and bottom 5 by pace
    print("\nTop 5 by pace (fastest):")
    top5 = driver_avg.nsmallest(5, 'lap_time')
    for idx, row in top5.iterrows():
        print(f"  #{int(idx)}: {row['lap_time']:.2f}s | "
              f"coast:{row['coasting_pct']:.1f}% | "
              f"G:{row['mean_g']:.2f} | "
              f"lift-offs:{row['lift_off_count']:.2f} | "
              f"full_thr:{row['full_throttle_pct']:.1f}%")

    print("\nBottom 5 by pace (slowest):")
    bottom5 = driver_avg.nlargest(5, 'lap_time')
    for idx, row in bottom5.iterrows():
        print(f"  #{int(idx)}: {row['lap_time']:.2f}s | "
              f"coast:{row['coasting_pct']:.1f}% | "
              f"G:{row['mean_g']:.2f} | "
              f"lift-offs:{row['lift_off_count']:.2f} | "
              f"full_thr:{row['full_throttle_pct']:.1f}%")

    # =========================================================================
    # CONCLUSION
    # =========================================================================
    print("\n" + "="*70)
    print("VALIDATION SUMMARY")
    print("="*70)

    # Count how many metrics have correct within-driver correlation
    correct_within = sum(
        1 for m in metrics_to_test
        if m in within_driver_corrs and
        ((within_driver_corrs[m] > 0 and expected_direction[m] == 'positive') or
         (within_driver_corrs[m] < 0 and expected_direction[m] == 'negative'))
    )

    print(f"\nWithin-driver correlations correct: {correct_within}/{len(metrics_to_test)}")

    if correct_within >= 3:
        print("PASS: Most metrics show expected relationship with lap time")
    else:
        print("FAIL: Metrics don't predict lap time as expected")

    print("\nInterpretation:")
    print("- Within-driver: When a driver's metric degrades, does lap time suffer?")
    print("- Cross-driver: Do faster drivers have better metrics on average?")


if __name__ == "__main__":
    main()
