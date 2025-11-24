"""
Exploratory Data Analysis for telemetry data.

Semantic analysis beyond basic loading:
1. Signal distributions and outliers
2. Missing value patterns
3. Sampling rate consistency
4. Cross-signal physical sanity checks
5. Per-driver variability

Usage:
    uv run python scripts/eda_telemetry.py
"""

from pathlib import Path
import pandas as pd
import numpy as np
from typing import Dict, List
import warnings
warnings.filterwarnings('ignore')

from motorsport_modeling.data.telemetry_loader import load_telemetry


def analyze_signal_distributions(df: pd.DataFrame) -> Dict:
    """Analyze distribution of each signal."""
    results = {}

    # Expected ranges based on domain knowledge
    expected_ranges = {
        'speed': (0, 300),           # km/h - max around 250-280 for GR86
        'throttle': (0, 100),        # percentage
        'aps': (0, 100),             # percentage
        'ath': (0, 100),             # percentage
        'pbrake_f': (0, 150),        # bar - typical max around 100-120
        'pbrake_r': (0, 150),        # bar
        'accx_can': (-2, 2),         # G - braking ~1.5G, accel ~0.8G
        'accy_can': (-3, 3),         # G - cornering up to 2G
        'Steering_Angle': (-540, 540),  # degrees - 1.5 turns lock-to-lock
        'gear': (0, 6),              # gears 1-6, 0=neutral
        'nmot': (0, 8000),           # RPM - redline around 7500
    }

    print("\n" + "="*70)
    print("SIGNAL DISTRIBUTIONS")
    print("="*70)

    for col in df.columns:
        if col in ['vehicle_number', 'lap', 'meta_time', 'time', 'timestamp']:
            continue

        if not pd.api.types.is_numeric_dtype(df[col]):
            continue

        data = df[col].dropna()
        if len(data) == 0:
            continue

        stats = {
            'count': len(data),
            'missing_pct': 100 * (len(df) - len(data)) / len(df),
            'min': data.min(),
            'max': data.max(),
            'mean': data.mean(),
            'std': data.std(),
            'p1': data.quantile(0.01),
            'p5': data.quantile(0.05),
            'p50': data.quantile(0.50),
            'p95': data.quantile(0.95),
            'p99': data.quantile(0.99),
            'zeros_pct': 100 * (data == 0).sum() / len(data),
        }

        # Check against expected range
        expected = expected_ranges.get(col)
        if expected:
            low, high = expected
            below = (data < low).sum()
            above = (data > high).sum()
            stats['below_range'] = below
            stats['above_range'] = above
            stats['out_of_range_pct'] = 100 * (below + above) / len(data)

        results[col] = stats

        # Print summary
        print(f"\n{col}:")
        print(f"  Range: [{stats['min']:.2f}, {stats['max']:.2f}]")
        print(f"  Mean: {stats['mean']:.2f}, Std: {stats['std']:.2f}")
        print(f"  Percentiles: P1={stats['p1']:.2f}, P50={stats['p50']:.2f}, P99={stats['p99']:.2f}")
        print(f"  Missing: {stats['missing_pct']:.1f}%, Zeros: {stats['zeros_pct']:.1f}%")

        if expected and stats.get('out_of_range_pct', 0) > 0:
            print(f"  WARNING: {stats['out_of_range_pct']:.2f}% outside expected [{low}, {high}]")

    return results


def analyze_missing_patterns(df: pd.DataFrame) -> Dict:
    """Analyze missing value patterns."""
    print("\n" + "="*70)
    print("MISSING VALUE PATTERNS")
    print("="*70)

    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    numeric_cols = [c for c in numeric_cols if c not in ['vehicle_number', 'lap']]

    # Overall missing by column
    missing_pct = df[numeric_cols].isna().mean() * 100
    print("\nMissing % by signal:")
    for col in missing_pct.sort_values(ascending=False).index:
        pct = missing_pct[col]
        if pct > 0:
            print(f"  {col}: {pct:.1f}%")

    # Are missing values correlated?
    if len(numeric_cols) >= 2:
        missing_matrix = df[numeric_cols].isna()

        # Find signals that are always missing together
        print("\nMissing value correlations (>0.8):")
        corr_found = False
        for i, col1 in enumerate(numeric_cols):
            for col2 in numeric_cols[i+1:]:
                if missing_matrix[col1].sum() > 0 and missing_matrix[col2].sum() > 0:
                    corr = missing_matrix[col1].corr(missing_matrix[col2])
                    if corr > 0.8:
                        print(f"  {col1} <-> {col2}: {corr:.2f}")
                        corr_found = True
        if not corr_found:
            print("  None found")

    # Missing by lap
    if 'lap' in df.columns:
        print("\nMissing % by lap (first 5 laps):")
        for lap in sorted(df['lap'].unique())[:5]:
            lap_data = df[df['lap'] == lap]
            missing = lap_data[numeric_cols].isna().mean().mean() * 100
            print(f"  Lap {int(lap)}: {missing:.1f}%")

    return {'missing_pct': missing_pct.to_dict()}


def analyze_sampling_rate(df: pd.DataFrame) -> Dict:
    """Analyze temporal sampling patterns."""
    print("\n" + "="*70)
    print("SAMPLING RATE ANALYSIS")
    print("="*70)

    results = {}

    if 'time' not in df.columns and 'meta_time' not in df.columns:
        print("No timestamp column found")
        return results

    time_col = 'time' if 'time' in df.columns else 'meta_time'

    # Ensure datetime
    df = df.copy()
    df['_time'] = pd.to_datetime(df[time_col], errors='coerce')

    # Overall sampling rate
    for veh in df['vehicle_number'].unique()[:3]:  # Sample 3 vehicles
        veh_data = df[df['vehicle_number'] == veh].sort_values('_time')

        if len(veh_data) < 10:
            continue

        deltas = veh_data['_time'].diff().dt.total_seconds().dropna()

        if len(deltas) == 0:
            continue

        # Filter out large gaps (between laps)
        deltas_filtered = deltas[deltas < 1.0]  # Less than 1 second

        if len(deltas_filtered) == 0:
            continue

        mean_hz = 1 / deltas_filtered.mean()
        std_hz = deltas_filtered.std() / (deltas_filtered.mean() ** 2)

        print(f"\nVehicle #{int(veh)}:")
        print(f"  Mean sampling rate: {mean_hz:.1f} Hz")
        print(f"  Delta range: [{deltas_filtered.min()*1000:.1f}, {deltas_filtered.max()*1000:.1f}] ms")
        print(f"  Gaps > 1s: {(deltas > 1.0).sum()}")

        results[int(veh)] = {
            'mean_hz': mean_hz,
            'min_delta_ms': deltas_filtered.min() * 1000,
            'max_delta_ms': deltas_filtered.max() * 1000,
            'gaps': int((deltas > 1.0).sum())
        }

    return results


def analyze_physical_sanity(df: pd.DataFrame) -> Dict:
    """Check if signals make physical sense together."""
    print("\n" + "="*70)
    print("PHYSICAL SANITY CHECKS")
    print("="*70)

    results = {}

    # 1. Braking should decelerate (negative accx_can when pbrake_f > 0)
    if 'pbrake_f' in df.columns and 'accx_can' in df.columns:
        braking = df['pbrake_f'] > 10  # Significant braking
        if braking.sum() > 0:
            decel = df.loc[braking, 'accx_can'] < 0
            pct_correct = 100 * decel.sum() / braking.sum()
            print(f"\n1. Braking -> deceleration:")
            print(f"   When pbrake_f > 10 bar, accx_can < 0: {pct_correct:.1f}%")
            results['brake_decel'] = pct_correct
            if pct_correct < 80:
                print(f"   WARNING: Expected >80%, got {pct_correct:.1f}%")

    # 2. Full throttle should accelerate (positive accx_can when throttle > 90)
    throttle_col = 'throttle' if 'throttle' in df.columns else ('aps' if 'aps' in df.columns else 'ath')
    if throttle_col in df.columns and 'accx_can' in df.columns:
        full_throttle = df[throttle_col] > 90
        if full_throttle.sum() > 0:
            # At full throttle in higher gears, should be accelerating
            accel = df.loc[full_throttle, 'accx_can'] > 0
            pct_correct = 100 * accel.sum() / full_throttle.sum()
            print(f"\n2. Full throttle -> acceleration:")
            print(f"   When {throttle_col} > 90%, accx_can > 0: {pct_correct:.1f}%")
            results['throttle_accel'] = pct_correct

    # 3. High lateral G should correlate with steering
    if 'accy_can' in df.columns and 'Steering_Angle' in df.columns:
        # When steering is significant, lateral G should be too
        steering = df['Steering_Angle'].abs() > 30  # More than 30 degrees
        if steering.sum() > 0:
            lat_g = df.loc[steering, 'accy_can'].abs() > 0.2
            pct_correct = 100 * lat_g.sum() / steering.sum()
            print(f"\n3. Steering -> lateral G:")
            print(f"   When |steering| > 30°, |accy_can| > 0.2: {pct_correct:.1f}%")
            results['steering_lat_g'] = pct_correct

    # 4. Combined G shouldn't exceed ~3G typically
    if 'accx_can' in df.columns and 'accy_can' in df.columns:
        combined_g = np.sqrt(df['accx_can']**2 + df['accy_can']**2)
        extreme = combined_g > 3.0
        pct_extreme = 100 * extreme.sum() / len(combined_g.dropna())
        print(f"\n4. Combined G-force:")
        print(f"   Max combined G: {combined_g.max():.2f}")
        print(f"   > 3G: {pct_extreme:.2f}%")
        results['max_combined_g'] = combined_g.max()
        if pct_extreme > 1:
            print(f"   WARNING: {pct_extreme:.2f}% above 3G may indicate sensor noise")

    # 5. Speed vs gear relationship
    if 'speed' in df.columns and 'gear' in df.columns:
        # In higher gears, speed should be higher
        gear_speed = df.groupby('gear')['speed'].median()
        print(f"\n5. Speed by gear (median km/h):")
        for gear in sorted(gear_speed.index):
            if gear > 0:
                print(f"   Gear {int(gear)}: {gear_speed[gear]:.1f} km/h")

        # Check if monotonically increasing
        speeds = [gear_speed.get(g, 0) for g in range(1, 7)]
        is_monotonic = all(speeds[i] <= speeds[i+1] for i in range(len(speeds)-1) if speeds[i] > 0 and speeds[i+1] > 0)
        results['gear_speed_monotonic'] = is_monotonic
        if not is_monotonic:
            print("   WARNING: Speed not monotonically increasing with gear")

    return results


def analyze_driver_variability(df: pd.DataFrame) -> Dict:
    """Analyze consistency across drivers."""
    print("\n" + "="*70)
    print("DRIVER VARIABILITY")
    print("="*70)

    results = {}

    if 'vehicle_number' not in df.columns:
        return results

    # Key metrics per driver
    key_signals = ['speed', 'pbrake_f', 'accx_can', 'accy_can']
    available = [s for s in key_signals if s in df.columns]

    print("\nSignal statistics by driver (sample of 5):")

    for signal in available:
        print(f"\n{signal}:")
        driver_stats = df.groupby('vehicle_number')[signal].agg(['mean', 'std', 'max'])

        # Show top/bottom drivers
        driver_stats = driver_stats.sort_values('mean')

        print(f"  Lowest mean: #{int(driver_stats.index[0])} = {driver_stats['mean'].iloc[0]:.2f}")
        print(f"  Highest mean: #{int(driver_stats.index[-1])} = {driver_stats['mean'].iloc[-1]:.2f}")
        print(f"  CV across drivers: {driver_stats['mean'].std() / driver_stats['mean'].mean() * 100:.1f}%")

        results[signal] = {
            'min_driver': int(driver_stats.index[0]),
            'max_driver': int(driver_stats.index[-1]),
            'cv': driver_stats['mean'].std() / driver_stats['mean'].mean() * 100
        }

    return results


def main():
    data_dir = Path(__file__).parent.parent / 'data' / 'raw' / 'tracks'

    # Test on one track first
    test_track = 'indianapolis'
    test_race = 'race1'

    race_dir = data_dir / test_track / test_race

    print("="*70)
    print(f"EDA: {test_track}/{test_race}")
    print("="*70)

    # Load data (sample of laps for speed)
    print("\nLoading telemetry...")
    df = load_telemetry(
        race_dir,
        laps=list(range(1, 11)),  # First 10 laps
        pivot_to_wide=True,
        verbose=True
    )

    # Run analyses
    dist_results = analyze_signal_distributions(df)
    missing_results = analyze_missing_patterns(df)
    sampling_results = analyze_sampling_rate(df)
    sanity_results = analyze_physical_sanity(df)
    driver_results = analyze_driver_variability(df)

    # Summary
    print("\n" + "="*70)
    print("EDA SUMMARY")
    print("="*70)

    # Key findings
    print("\nKey Findings:")

    # 1. Missing data
    high_missing = [k for k, v in dist_results.items() if v.get('missing_pct', 0) > 20]
    if high_missing:
        print(f"  - High missing data (>20%): {high_missing}")

    # 2. Out of range
    out_of_range = [k for k, v in dist_results.items() if v.get('out_of_range_pct', 0) > 1]
    if out_of_range:
        print(f"  - Out of expected range (>1%): {out_of_range}")

    # 3. Physical sanity issues
    sanity_issues = [k for k, v in sanity_results.items() if isinstance(v, (int, float)) and v < 80]
    if sanity_issues:
        print(f"  - Physical sanity concerns: {sanity_issues}")

    print("\n" + "="*70)
    print("EDA COMPLETE")
    print("="*70)


if __name__ == "__main__":
    main()
