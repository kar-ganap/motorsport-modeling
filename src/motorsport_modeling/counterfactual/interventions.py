"""
Counterfactual Intervention Generator

Generates "what if" scenarios by modifying driver-controllable features
and predicting the impact on lap times and race position.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from .lap_time_model import LapTimeModel


@dataclass
class Intervention:
    """Single counterfactual intervention on a driver-controllable feature."""
    feature: str                    # Feature being modified
    original_value: float           # Original feature value
    modified_value: float           # Modified feature value
    predicted_delta: float          # Predicted change in lap time delta (s)
    predicted_time_savings: float   # Total time savings over race (s)
    description: str                # Human-readable description


@dataclass
class CounterfactualScenario:
    """Complete counterfactual scenario for a driver with multiple interventions."""
    vehicle_number: int
    original_position: int
    original_avg_lap_time: float
    original_gap_to_winner: float

    interventions: List[Intervention]
    total_time_savings: float       # Sum of all interventions
    predicted_position_gain: int    # Estimated positions gained

    # Realistic improvement bounds (field benchmark)
    field_p25_degradation: float    # 25th percentile degradation (better than median)
    field_p25_consistency: float    # 25th percentile consistency (better than median)
    field_min_traffic: float        # Minimum traffic laps in field

    def get_best_intervention(self) -> Optional[Intervention]:
        """Get intervention with largest predicted impact."""
        if not self.interventions:
            return None
        return max(self.interventions, key=lambda x: x.predicted_time_savings)

    def summary(self) -> str:
        """Generate human-readable summary."""
        if not self.interventions:
            return f"Driver #{self.vehicle_number}: No interventions available"

        best = self.get_best_intervention()

        lines = [
            f"Driver #{self.vehicle_number} - P{self.original_position}",
            f"Original avg lap time: {self.original_avg_lap_time:.3f}s",
            f"Gap to winner: {self.original_gap_to_winner:.1f}s",
            "",
            f"Counterfactual Interventions ({len(self.interventions)} total):",
        ]

        for i, intervention in enumerate(sorted(self.interventions,
                                                 key=lambda x: x.predicted_time_savings,
                                                 reverse=True), 1):
            lines.append(f"  {i}. {intervention.description}")
            lines.append(f"     Time savings: {intervention.predicted_time_savings:.2f}s")

        lines.extend([
            "",
            f"Total potential time savings: {self.total_time_savings:.2f}s",
            f"Estimated position gain: +{self.predicted_position_gain} positions" if self.predicted_position_gain > 0 else "No position gain predicted",
        ])

        return "\n".join(lines)


def generate_interventions(
    model: LapTimeModel,
    driver_features: pd.Series,
    features_df: pd.DataFrame,
    num_laps: int = 20
) -> CounterfactualScenario:
    """
    Generate counterfactual interventions for a single driver.

    Args:
        model: Trained LapTimeModel
        driver_features: Driver's current features (Series from extract_race_features)
        features_df: All drivers' features (for field benchmarks)
        num_laps: Number of race laps (for time savings calculation)

    Returns:
        CounterfactualScenario with all generated interventions
    """
    interventions = []

    # Field benchmarks (for realistic improvement targets)
    field_p25_deg = features_df['controllable_degradation_rate'].quantile(0.25)
    field_p25_cons = features_df['controllable_consistency'].quantile(0.25)
    field_min_traffic = features_df['controllable_traffic_laps'].min()

    # INTERVENTION 1: Improve tire degradation to field P25 (top 25% performance)
    current_deg = driver_features['controllable_degradation_rate']
    if current_deg > field_p25_deg:
        # Create modified feature vector
        modified_features = driver_features.copy()
        modified_features['controllable_degradation_rate'] = field_p25_deg

        # Predict impact
        original_delta = driver_features['lap_time_delta']
        predicted_delta = model.predict(pd.DataFrame([modified_features]))[0]
        delta_improvement = original_delta - predicted_delta  # Positive = faster

        # Time savings over full race
        time_savings = delta_improvement * num_laps

        interventions.append(Intervention(
            feature='degradation_rate',
            original_value=current_deg,
            modified_value=field_p25_deg,
            predicted_delta=predicted_delta,
            predicted_time_savings=time_savings,
            description=f"Improve tire management: {current_deg:.4f} → {field_p25_deg:.4f} s/lap (field P25)"
        ))

    # INTERVENTION 2: Improve consistency to field P25
    current_cons = driver_features['controllable_consistency']
    if current_cons > field_p25_cons:
        modified_features = driver_features.copy()
        modified_features['controllable_consistency'] = field_p25_cons

        original_delta = driver_features['lap_time_delta']
        predicted_delta = model.predict(pd.DataFrame([modified_features]))[0]
        delta_improvement = original_delta - predicted_delta
        time_savings = delta_improvement * num_laps

        interventions.append(Intervention(
            feature='consistency',
            original_value=current_cons,
            modified_value=field_p25_cons,
            predicted_delta=predicted_delta,
            predicted_time_savings=time_savings,
            description=f"Improve lap consistency: {current_cons:.3f} → {field_p25_cons:.3f}s std dev (field P25)"
        ))

    # INTERVENTION 3: Reduce traffic laps to field minimum
    current_traffic = driver_features['controllable_traffic_laps']
    if current_traffic > field_min_traffic:
        modified_features = driver_features.copy()
        modified_features['controllable_traffic_laps'] = field_min_traffic

        original_delta = driver_features['lap_time_delta']
        predicted_delta = model.predict(pd.DataFrame([modified_features]))[0]
        delta_improvement = original_delta - predicted_delta
        time_savings = delta_improvement * num_laps

        laps_avoided = int(current_traffic - field_min_traffic)

        interventions.append(Intervention(
            feature='traffic_laps',
            original_value=current_traffic,
            modified_value=field_min_traffic,
            predicted_delta=predicted_delta,
            predicted_time_savings=time_savings,
            description=f"Avoid traffic: {int(current_traffic)} → {int(field_min_traffic)} laps (avoid {laps_avoided} laps in traffic)"
        ))

    # Calculate total time savings
    total_time_savings = sum(i.predicted_time_savings for i in interventions)

    # Estimate position gain
    # Simple heuristic: compare to gaps between positions
    original_gap_to_winner = driver_features.get('gap_to_winner', 0.0)

    # Find how many positions could be gained
    positions_gained = 0
    if 'final_position' in features_df.columns:
        current_pos = driver_features['final_position']

        # Check drivers ahead
        drivers_ahead = features_df[features_df['final_position'] < current_pos].copy()
        if len(drivers_ahead) > 0:
            # Sort by position (descending, so closest competitor first)
            drivers_ahead = drivers_ahead.sort_values('final_position', ascending=False)

            time_saved_so_far = total_time_savings
            for _, ahead_driver in drivers_ahead.iterrows():
                # Rough estimate: if we saved more time than our pace delta with them
                pace_diff = driver_features['avg_lap_time'] - ahead_driver['avg_lap_time']
                time_gap = pace_diff * num_laps  # Estimated total time difference

                if time_saved_so_far > abs(time_gap):
                    positions_gained += 1
                    time_saved_so_far -= abs(time_gap)
                else:
                    break

    return CounterfactualScenario(
        vehicle_number=int(driver_features['vehicle_number']),
        original_position=int(driver_features['final_position']),
        original_avg_lap_time=float(driver_features['avg_lap_time']),
        original_gap_to_winner=float(original_gap_to_winner) if pd.notna(original_gap_to_winner) else 0.0,
        interventions=interventions,
        total_time_savings=total_time_savings,
        predicted_position_gain=positions_gained,
        field_p25_degradation=field_p25_deg,
        field_p25_consistency=field_p25_cons,
        field_min_traffic=field_min_traffic,
    )


def generate_all_interventions(
    model: LapTimeModel,
    features_df: pd.DataFrame,
    num_laps: int = 20
) -> List[CounterfactualScenario]:
    """
    Generate counterfactual scenarios for all drivers.

    Args:
        model: Trained LapTimeModel
        features_df: All drivers' features from extract_race_features
        num_laps: Number of race laps

    Returns:
        List of CounterfactualScenario, one per driver
    """
    scenarios = []

    for idx, driver_features in features_df.iterrows():
        try:
            scenario = generate_interventions(model, driver_features, features_df, num_laps)
            scenarios.append(scenario)
        except Exception as e:
            print(f"Warning: Could not generate interventions for driver #{int(driver_features['vehicle_number'])}: {e}")

    return scenarios


def interventions_to_dataframe(scenarios: List[CounterfactualScenario]) -> pd.DataFrame:
    """
    Convert counterfactual scenarios to DataFrame for easy analysis/export.

    Args:
        scenarios: List of CounterfactualScenario

    Returns:
        DataFrame with one row per driver and columns for each intervention
    """
    rows = []

    for scenario in scenarios:
        row = {
            'vehicle_number': scenario.vehicle_number,
            'original_position': scenario.original_position,
            'original_avg_lap_time': scenario.original_avg_lap_time,
            'original_gap_to_winner': scenario.original_gap_to_winner,
            'total_time_savings': scenario.total_time_savings,
            'predicted_position_gain': scenario.predicted_position_gain,
            'num_interventions': len(scenario.interventions),
        }

        # Add individual intervention details
        for intervention in scenario.interventions:
            prefix = f'intervention_{intervention.feature}'
            row[f'{prefix}_original'] = intervention.original_value
            row[f'{prefix}_target'] = intervention.modified_value
            row[f'{prefix}_savings'] = intervention.predicted_time_savings

        # Add field benchmarks
        row['field_p25_degradation'] = scenario.field_p25_degradation
        row['field_p25_consistency'] = scenario.field_p25_consistency
        row['field_min_traffic'] = scenario.field_min_traffic

        rows.append(row)

    return pd.DataFrame(rows)
