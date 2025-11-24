#!/usr/bin/env python3
"""
Find the best (track, race) combo for Model Validation demo.
Analyzes which race shows the clearest monotonic trends:
1. More warm-up laps → lower MAE (left-to-right improvement)
2. Longer horizon → higher MAE (bottom-to-top degradation)
"""

import pandas as pd
import numpy as np
from pathlib import Path
from scipy.stats import spearmanr

def analyze_monotonic_trends():
    """Find race with strongest monotonic trends in both directions."""

    data_dir = Path('data/processed')
    results = []

    # Process each validation file
    for val_file in data_dir.glob('*/*_validation.parquet'):
        track = val_file.parent.name
        race = val_file.stem.replace('_validation', '')

        # Load validation data
        df = pd.read_parquet(val_file)

        # Calculate MAE for each (warmup, horizon) combination
        mae_grid = df.groupby(['warmup_laps', 'horizon'])['abs_error'].mean().reset_index()
        mae_grid.columns = ['warmup_laps', 'horizon', 'mae']

        if len(mae_grid) < 10:  # Need enough points to assess trends
            continue

        # Trend 1: For each horizon, check if MAE decreases with more warmup laps
        warmup_trend_scores = []
        for horizon in mae_grid['horizon'].unique():
            horizon_data = mae_grid[mae_grid['horizon'] == horizon].sort_values('warmup_laps')
            if len(horizon_data) >= 3:
                # Spearman correlation: negative = MAE decreases as warmup increases (good)
                corr, _ = spearmanr(horizon_data['warmup_laps'], horizon_data['mae'])
                warmup_trend_scores.append(-corr)  # Negate so negative correlation = positive score

        # Trend 2: For each warmup, check if MAE increases with longer horizon
        horizon_trend_scores = []
        for warmup in mae_grid['warmup_laps'].unique():
            warmup_data = mae_grid[mae_grid['warmup_laps'] == warmup].sort_values('horizon')
            if len(warmup_data) >= 3:
                # Spearman correlation: positive = MAE increases as horizon increases (good)
                corr, _ = spearmanr(warmup_data['horizon'], warmup_data['mae'])
                horizon_trend_scores.append(corr)

        if not warmup_trend_scores or not horizon_trend_scores:
            continue

        # Average trend strength
        warmup_trend = np.mean(warmup_trend_scores)
        horizon_trend = np.mean(horizon_trend_scores)

        # Combined score: both trends should be strong and positive
        combined_score = warmup_trend * horizon_trend  # Multiply to require both to be good

        # Also get the overall MAE for reference
        overall_mae = df['abs_error'].mean()

        results.append({
            'track': track,
            'race': race,
            'warmup_trend': warmup_trend,
            'horizon_trend': horizon_trend,
            'combined_score': combined_score,
            'overall_mae': overall_mae,
            'n_points': len(mae_grid)
        })

    # Convert to DataFrame and sort by combined score
    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values('combined_score', ascending=False)

    return results_df

if __name__ == '__main__':
    print('='*80)
    print('FINDING BEST (TRACK, RACE) FOR MODEL VALIDATION DEMO')
    print('='*80)
    print()
    print('Criteria: Strongest monotonic trends in BOTH directions:')
    print('  1. More warm-up laps → lower MAE (warmup_trend score)')
    print('  2. Longer horizon → higher MAE (horizon_trend score)')
    print()

    results = analyze_monotonic_trends()

    print('Top 10 Races with Strongest Trends:')
    print('='*80)
    print(results.head(10).to_string(index=False, float_format='%.3f'))
    print()

    print('Bottom 5 Races with Weakest Trends:')
    print('='*80)
    print(results.tail(5).to_string(index=False, float_format='%.3f'))
    print()

    # Highlight the winner
    best = results.iloc[0]
    print('='*80)
    print('RECOMMENDED FOR DEMO:')
    print('='*80)
    print(f'Track: {best["track"].title()}')
    print(f'Race: {best["race"].title()}')
    print(f'Warmup Trend Score: {best["warmup_trend"]:.3f} (higher = clearer improvement with more laps)')
    print(f'Horizon Trend Score: {best["horizon_trend"]:.3f} (higher = clearer degradation with longer horizon)')
    print(f'Combined Score: {best["combined_score"]:.3f} (product of both trends)')
    print(f'Overall MAE: {best["overall_mae"]:.3f} seconds (for reference)')
    print(f'Grid points: {int(best["n_points"])} (warmup, horizon) combinations')
    print()
    print('This race shows the CLEAREST demonstration of both monotonic trends.')
