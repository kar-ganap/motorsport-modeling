"""
Validate Tier 1 metrics: P1 should outscore P19 on ≥4 of 5 metrics.

Usage:
    uv run python scripts/validate_tier1_metrics_v2.py
"""

from pathlib import Path
import pandas as pd
import numpy as np

from motorsport_modeling.data.telemetry_loader import load_telemetry, load_lap_times
from motorsport_modeling.metrics.tier1_metrics import compute_metrics_for_race


def main():
    data_dir = Path(__file__).parent.parent / 'data' / 'raw' / 'tracks'

    # Test on Indianapolis Race 1
    track = 'indianapolis'
    race = 'race1'
    race_dir = data_dir / track / race

    print("="*70)
    print(f"TIER 1 METRICS VALIDATION: {track}/{race}")
    print("="*70)

    # Load telemetry
    print("\nLoading telemetry...")
    telemetry = load_telemetry(
        race_dir,
        laps=list(range(1, 21)),  # First 20 laps
        pivot_to_wide=True,
        verbose=True
    )

    # Load lap times
    print("\nLoading lap times...")
    lap_times = load_lap_times(race_dir)
    print(f"Loaded {len(lap_times)} lap time records")

    # Compute metrics for all drivers
    print("\nComputing metrics for all drivers...")
    metrics_df = compute_metrics_for_race(telemetry, lap_times, per_lap=False)

    print(f"\nMetrics computed for {len(metrics_df)} drivers")
    print("\nMetrics columns:", list(metrics_df.columns))

    # Load race results to get P1 and P19
    results_files = list(race_dir.glob('*Results*.CSV'))
    if results_files:
        results = pd.read_csv(results_files[0], sep=';')
        results.columns = results.columns.str.strip()

        if 'POSITION' in results.columns and 'NUMBER' in results.columns:
            # Get P1 and P19
            p1_num = int(results[results['POSITION'] == 1]['NUMBER'].iloc[0])
            p19_row = results[results['POSITION'] == 19]
            if len(p19_row) > 0:
                p19_num = int(p19_row['NUMBER'].iloc[0])
            else:
                # Get last place
                p19_num = int(results.iloc[-1]['NUMBER'])
                p19_pos = int(results.iloc[-1]['POSITION'])
                print(f"  Note: Using P{p19_pos} instead of P19")

            print(f"\nComparing P1 (#{p1_num}) vs P19/last (#{p19_num})")
        else:
            # Fallback: use first and last in metrics
            p1_num = metrics_df['vehicle_number'].iloc[0]
            p19_num = metrics_df['vehicle_number'].iloc[-1]
    else:
        p1_num = metrics_df['vehicle_number'].iloc[0]
        p19_num = metrics_df['vehicle_number'].iloc[-1]

    # Get metrics for P1 and P19
    p1_metrics = metrics_df[metrics_df['vehicle_number'] == p1_num].iloc[0]
    p19_metrics = metrics_df[metrics_df['vehicle_number'] == p19_num].iloc[0]

    # Compare metrics
    print("\n" + "="*70)
    print("METRIC COMPARISON")
    print("="*70)

    # Define what "better" means for each metric
    metrics_comparison = {
        'consistency_std': ('lower', 'Consistency (lap time σ)'),
        'coasting_pct': ('lower', 'Coasting %'),  # Lower = more committed
        'brake_oscillations_per_event': ('lower', 'Brake smoothness (osc/event)'),
        'apex_to_throttle_ms': ('lower', 'Throttle timing (apex→full)'),
        'mean_combined_g': ('higher', 'G-force utilization'),
    }

    p1_wins = 0
    total_metrics = 0

    for metric, (direction, name) in metrics_comparison.items():
        p1_val = p1_metrics.get(metric, np.nan)
        p19_val = p19_metrics.get(metric, np.nan)

        if pd.isna(p1_val) or pd.isna(p19_val):
            print(f"\n{name}:")
            print(f"  P1 (#{p1_num}): {p1_val}")
            print(f"  P19 (#{p19_num}): {p19_val}")
            print(f"  Result: SKIPPED (missing data)")
            continue

        total_metrics += 1

        if direction == 'lower':
            p1_better = p1_val < p19_val
        else:
            p1_better = p1_val > p19_val

        if p1_better:
            p1_wins += 1
            result = "P1 WINS"
        else:
            result = "P19 wins"

        print(f"\n{name}:")
        print(f"  P1 (#{p1_num}): {p1_val:.2f}")
        print(f"  P19 (#{p19_num}): {p19_val:.2f}")
        print(f"  Better: {direction} -> {result}")

    # Summary
    print("\n" + "="*70)
    print("VALIDATION RESULT")
    print("="*70)

    print(f"\nP1 wins on {p1_wins} of {total_metrics} metrics")

    if p1_wins >= 4:
        print("SUCCESS: P1 outscores P19 on ≥4 metrics!")
    elif p1_wins >= 3:
        print("PARTIAL: P1 outscores on 3 metrics (target is 4)")
    else:
        print(f"FAIL: P1 only outscores on {p1_wins} metrics")

    # Show all metrics for debugging
    print("\n" + "="*70)
    print("ALL DRIVER METRICS (sorted by mean_combined_g)")
    print("="*70)

    display_cols = ['vehicle_number', 'consistency_std', 'coasting_pct',
                    'brake_oscillations_per_event', 'apex_to_throttle_ms', 'mean_combined_g']
    display_cols = [c for c in display_cols if c in metrics_df.columns]

    sorted_df = metrics_df[display_cols].sort_values('mean_combined_g', ascending=False)
    print(sorted_df.head(10).to_string())


if __name__ == "__main__":
    main()
