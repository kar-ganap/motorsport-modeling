#!/usr/bin/env python3
"""
Find the best (track, race) combo for Model Validation demo.
Analyzes all validation files and finds lowest MAE for warmup=5, horizon=1.
"""

import pandas as pd
from pathlib import Path

def analyze_validation_files():
    """Analyze all validation files and find best performing race."""

    data_dir = Path('data/processed')
    results = []

    # Process each validation file
    for val_file in data_dir.glob('*/*_validation.parquet'):
        track = val_file.parent.name
        race = val_file.stem.replace('_validation', '')

        # Load validation data
        df = pd.read_parquet(val_file)

        # Filter for warmup=5, horizon=1
        filtered = df[(df['warmup_laps'] == 5) & (df['horizon'] == 1)]

        if len(filtered) == 0:
            continue

        # Calculate MAE (mean of abs_error)
        mae = filtered['abs_error'].mean()

        # Get additional stats
        median_ae = filtered['abs_error'].median()
        max_ae = filtered['abs_error'].max()
        n_predictions = len(filtered)

        results.append({
            'track': track,
            'race': race,
            'mae': mae,
            'median_ae': median_ae,
            'max_ae': max_ae,
            'n_predictions': n_predictions
        })

    # Convert to DataFrame and sort by MAE
    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values('mae')

    return results_df

if __name__ == '__main__':
    print('='*80)
    print('FINDING BEST (TRACK, RACE) FOR MODEL VALIDATION DEMO')
    print('='*80)
    print()
    print('Criteria: Lowest MAE for warmup_laps=5, horizon=1')
    print()

    results = analyze_validation_files()

    print('Top 10 Best Performing Races:')
    print('='*80)
    print(results.head(10).to_string(index=False))
    print()

    print('Bottom 5 Worst Performing Races:')
    print('='*80)
    print(results.tail(5).to_string(index=False))
    print()

    # Highlight the winner
    best = results.iloc[0]
    print('='*80)
    print('RECOMMENDED FOR DEMO:')
    print('='*80)
    print(f'Track: {best["track"].title()}')
    print(f'Race: {best["race"].title()}')
    print(f'MAE: {best["mae"]:.3f} seconds')
    print(f'Median AE: {best["median_ae"]:.3f} seconds')
    print(f'Max AE: {best["max_ae"]:.3f} seconds')
    print(f'Number of predictions: {best["n_predictions"]}')
    print()
