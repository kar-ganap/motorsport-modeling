"""
Prepare lap time features for modeling.

This script:
1. Loads lap time data for Race 1 and Race 2
2. Computes race features (positions, gaps, context)
3. Saves feature matrices for training

Usage:
    uv run python scripts/prepare_lap_features.py
"""

from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from motorsport_modeling.models.feature_engineering import (
    prepare_race_features,
    get_feature_columns
)


def main():
    data_dir = Path(__file__).parent.parent / 'data' / 'raw'
    output_dir = Path(__file__).parent.parent / 'data' / 'processed'
    output_dir.mkdir(exist_ok=True)

    # Process Race 1
    print("\n" + "=" * 70)
    print("RACE 1 FEATURE ENGINEERING")
    print("=" * 70)

    r1_file = data_dir / 'R1_indianapolis_motor_speedway_lap_time.csv'
    r1_weather = data_dir / '26_Weather_Race 1.CSV'
    r1_endurance = data_dir / '23_AnalysisEnduranceWithSections_Race 1.CSV'

    r1_features = prepare_race_features(
        r1_file,
        total_laps=26,
        weather_file=r1_weather,
        endurance_file=r1_endurance,
        verbose=True
    )

    # Save Race 1 features
    r1_output = output_dir / 'race1_features.csv'
    r1_features.to_csv(r1_output, index=False)
    print(f"\nSaved: {r1_output}")

    # Process Race 2
    print("\n" + "=" * 70)
    print("RACE 2 FEATURE ENGINEERING")
    print("=" * 70)

    r2_file = data_dir / 'R2_indianapolis_motor_speedway_lap_time.csv'
    r2_weather = data_dir / '26_Weather_Race 2.CSV'
    r2_endurance = data_dir / '23_AnalysisEnduranceWithSections_Race 2.CSV'

    r2_features = prepare_race_features(
        r2_file,
        total_laps=26,
        weather_file=r2_weather,
        endurance_file=r2_endurance,
        verbose=True
    )

    # Save Race 2 features
    r2_output = output_dir / 'race2_features.csv'
    r2_features.to_csv(r2_output, index=False)
    print(f"\nSaved: {r2_output}")

    # Summary statistics
    print("\n" + "=" * 70)
    print("DATA SUMMARY")
    print("=" * 70)

    print("\nRace 1:")
    print(f"  Rows: {len(r1_features)}")
    print(f"  Vehicles: {r1_features['vehicle_number'].nunique()}")
    print(f"  Lap times: {r1_features['lap_time'].min():.3f}s - {r1_features['lap_time'].max():.3f}s")
    print(f"  Mean lap time: {r1_features['lap_time'].mean():.3f}s")

    print("\nRace 2:")
    print(f"  Rows: {len(r2_features)}")
    print(f"  Vehicles: {r2_features['vehicle_number'].nunique()}")
    print(f"  Lap times: {r2_features['lap_time'].min():.3f}s - {r2_features['lap_time'].max():.3f}s")
    print(f"  Mean lap time: {r2_features['lap_time'].mean():.3f}s")

    # Visualize
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # Plot 1: Lap times over race (Race 1)
    ax1 = axes[0, 0]
    for vehicle in [55, 2, 113]:  # Winner, runner-up, backmarker
        vehicle_data = r1_features[r1_features['vehicle_number'] == vehicle]
        ax1.plot(vehicle_data['lap'], vehicle_data['lap_time'],
                label=f'#{vehicle}', marker='o', markersize=3)
    ax1.set_xlabel('Lap')
    ax1.set_ylabel('Lap Time (s)')
    ax1.set_title('Race 1: Lap Times')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # Plot 2: Positions over race (Race 1)
    ax2 = axes[0, 1]
    for vehicle in [55, 2, 113]:
        vehicle_data = r1_features[r1_features['vehicle_number'] == vehicle]
        ax2.plot(vehicle_data['lap'], vehicle_data['position'],
                label=f'#{vehicle}', marker='o', markersize=3)
    ax2.set_xlabel('Lap')
    ax2.set_ylabel('Position')
    ax2.set_title('Race 1: Positions')
    ax2.invert_yaxis()  # P1 at top
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    # Plot 3: Gap to leader (Race 1)
    ax3 = axes[1, 0]
    for vehicle in [55, 2, 113]:
        vehicle_data = r1_features[r1_features['vehicle_number'] == vehicle]
        ax3.plot(vehicle_data['lap'], vehicle_data['gap_to_leader'],
                label=f'#{vehicle}', marker='o', markersize=3)
    ax3.set_xlabel('Lap')
    ax3.set_ylabel('Gap to Leader (s)')
    ax3.set_title('Race 1: Gap to Leader')
    ax3.legend()
    ax3.grid(True, alpha=0.3)

    # Plot 4: Lap time distribution
    ax4 = axes[1, 1]
    r1_features['lap_time'].hist(bins=50, ax=ax4, alpha=0.7, label='Race 1')
    r2_features['lap_time'].hist(bins=50, ax=ax4, alpha=0.7, label='Race 2')
    ax4.set_xlabel('Lap Time (s)')
    ax4.set_ylabel('Count')
    ax4.set_title('Lap Time Distribution')
    ax4.legend()
    ax4.grid(True, alpha=0.3)

    plt.tight_layout()

    # Save figure
    fig_output = Path(__file__).parent.parent / 'outputs' / 'lap_features_summary.png'
    plt.savefig(fig_output, dpi=150, bbox_inches='tight')
    print(f"\nSaved visualization: {fig_output}")

    # Show feature columns
    print("\n" + "=" * 70)
    print("FEATURE COLUMNS")
    print("=" * 70)

    feature_cols = get_feature_columns()
    for category, cols in feature_cols.items():
        if cols:
            print(f"\n{category.upper()}:")
            for col in cols:
                print(f"  - {col}")

    # Show sample data
    print("\n" + "=" * 70)
    print("SAMPLE DATA (Race 1, Lap 10)")
    print("=" * 70)

    sample = r1_features[r1_features['lap'] == 10].sort_values('position')
    print(sample[['vehicle_number', 'lap', 'lap_time', 'position',
                  'gap_to_leader', 'gap_to_ahead', 'gap_to_behind']].head(10).to_string())

    print("\n" + "=" * 70)

    return r1_features, r2_features


if __name__ == "__main__":
    main()
