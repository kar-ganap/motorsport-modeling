"""
DriverProfile - Computes and stores driver characteristics.

Separates metrics into:
- Profile features: Stable traits that characterize skill level
- State baselines: Dynamic measures for comparison during race

Usage:
    from motorsport_modeling.coaching import DriverProfile

    # Build profile from practice/qualifying laps
    profile = DriverProfile.from_telemetry(telemetry, vehicle_number=72, laps=[1,2,3,4,5])

    # Get profile summary
    print(profile.profile_features)
    print(profile.state_baselines)

    # Compare to field
    field_comparison = profile.compare_to_field(all_profiles)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import pandas as pd
import numpy as np

from ..metrics.tier1_metrics import (
    compute_coasting_pct,
    compute_braking_smoothness,
    compute_g_force_utilization,
    compute_throttle_timing
)


@dataclass
class DriverProfile:
    """
    Driver profile containing stable traits and state baselines.

    Profile features (stable traits - compare across field):
    - lift_off_count: Traction management ability
    - mean_combined_g: Grip utilization ability
    - full_throttle_pct: Commitment level

    State baselines (dynamic - compare to self):
    - brake_cv: Braking consistency (mean and std)
    - coasting_pct: Commitment/hesitation (mean and std)
    """

    vehicle_number: int

    # Profile features (mean values - stable traits)
    lift_off_count: float = 0.0
    mean_combined_g: float = 0.0
    full_throttle_pct: float = 0.0

    # State baselines (mean and std for comparison)
    brake_cv_mean: float = 0.0
    brake_cv_std: float = 0.0
    coasting_pct_mean: float = 0.0
    coasting_pct_std: float = 0.0

    # Metadata
    laps_used: int = 0

    # Per-lap data for trend analysis
    lap_data: List[Dict] = field(default_factory=list)

    @property
    def profile_features(self) -> Dict[str, float]:
        """Get profile features for skill assessment."""
        return {
            'lift_off_count': self.lift_off_count,
            'mean_combined_g': self.mean_combined_g,
            'full_throttle_pct': self.full_throttle_pct
        }

    @property
    def state_baselines(self) -> Dict[str, Dict[str, float]]:
        """Get state baselines for real-time comparison."""
        return {
            'brake_cv': {
                'mean': self.brake_cv_mean,
                'std': self.brake_cv_std
            },
            'coasting_pct': {
                'mean': self.coasting_pct_mean,
                'std': self.coasting_pct_std
            }
        }

    @classmethod
    def from_telemetry(
        cls,
        telemetry: pd.DataFrame,
        vehicle_number: int,
        laps: Optional[List[int]] = None
    ) -> 'DriverProfile':
        """
        Build driver profile from telemetry data.

        Parameters
        ----------
        telemetry : pd.DataFrame
            Telemetry data in wide format
        vehicle_number : int
            Car number
        laps : list of int, optional
            Laps to use for profile. If None, uses all available.

        Returns
        -------
        DriverProfile
            Computed profile for the driver
        """
        # Filter to this vehicle
        veh_data = telemetry[telemetry['vehicle_number'] == vehicle_number]

        if laps is None:
            laps = sorted(veh_data['lap'].dropna().unique())

        # Compute per-lap metrics
        lap_metrics = []

        for lap in laps:
            try:
                coasting = compute_coasting_pct(telemetry, vehicle_number, lap)
                braking = compute_braking_smoothness(telemetry, vehicle_number, lap)
                g_force = compute_g_force_utilization(telemetry, vehicle_number, lap)
                throttle = compute_throttle_timing(telemetry, vehicle_number, lap)

                lap_metrics.append({
                    'lap': lap,
                    'coasting_pct': coasting['coasting_pct'],
                    'brake_cv': braking.get('peak_brake_cv', np.nan),
                    'mean_combined_g': g_force['mean_combined_g'],
                    'lift_off_count': throttle.get('lift_off_count', np.nan),
                    'full_throttle_pct': throttle.get('full_throttle_pct', np.nan)
                })
            except Exception:
                # Skip laps with errors
                continue

        if not lap_metrics:
            # Return empty profile
            return cls(vehicle_number=vehicle_number)

        # Convert to DataFrame for aggregation
        df = pd.DataFrame(lap_metrics)

        # Compute profile features (means of stable traits)
        lift_off_count = df['lift_off_count'].mean()
        mean_combined_g = df['mean_combined_g'].mean()
        full_throttle_pct = df['full_throttle_pct'].mean()

        # Compute state baselines (mean and std for dynamic measures)
        brake_cv_mean = df['brake_cv'].mean()
        brake_cv_std = df['brake_cv'].std()
        coasting_pct_mean = df['coasting_pct'].mean()
        coasting_pct_std = df['coasting_pct'].std()

        # Handle NaN std (single lap)
        if pd.isna(brake_cv_std):
            brake_cv_std = brake_cv_mean * 0.15  # Assume 15% CV as default
        if pd.isna(coasting_pct_std):
            coasting_pct_std = coasting_pct_mean * 0.15

        return cls(
            vehicle_number=vehicle_number,
            lift_off_count=lift_off_count,
            mean_combined_g=mean_combined_g,
            full_throttle_pct=full_throttle_pct,
            brake_cv_mean=brake_cv_mean,
            brake_cv_std=brake_cv_std,
            coasting_pct_mean=coasting_pct_mean,
            coasting_pct_std=coasting_pct_std,
            laps_used=len(lap_metrics),
            lap_data=lap_metrics
        )

    def compare_to_field(
        self,
        field_profiles: List['DriverProfile']
    ) -> Dict[str, Dict]:
        """
        Compare this driver's profile to the field.

        Parameters
        ----------
        field_profiles : list of DriverProfile
            All driver profiles in the field

        Returns
        -------
        dict
            Comparison results with percentile rankings
        """
        if not field_profiles:
            return {}

        # Get field distributions
        field_lift_offs = [p.lift_off_count for p in field_profiles if p.lift_off_count > 0]
        field_g_force = [p.mean_combined_g for p in field_profiles if p.mean_combined_g > 0]
        field_full_throttle = [p.full_throttle_pct for p in field_profiles if p.full_throttle_pct > 0]

        comparisons = {}

        # Lift-off count (lower is better)
        if field_lift_offs:
            percentile = 100 * sum(1 for x in field_lift_offs if x > self.lift_off_count) / len(field_lift_offs)
            field_mean = np.mean(field_lift_offs)
            ratio = self.lift_off_count / field_mean if field_mean > 0 else 1.0

            comparisons['lift_off_count'] = {
                'value': self.lift_off_count,
                'percentile': percentile,  # Higher = better (fewer lift-offs)
                'vs_field': f"{ratio:.1f}x avg",
                'field_mean': field_mean,
                'interpretation': 'traction_management'
            }

        # G-force utilization (higher is better)
        if field_g_force:
            percentile = 100 * sum(1 for x in field_g_force if x < self.mean_combined_g) / len(field_g_force)
            field_mean = np.mean(field_g_force)

            # Determine quartile
            sorted_g = sorted(field_g_force, reverse=True)
            rank = sum(1 for x in sorted_g if x > self.mean_combined_g) + 1

            if rank <= len(sorted_g) * 0.25:
                quartile = "Top 25%"
            elif rank <= len(sorted_g) * 0.5:
                quartile = "Top 50%"
            elif rank <= len(sorted_g) * 0.75:
                quartile = "Bottom 50%"
            else:
                quartile = "Bottom 25%"

            comparisons['mean_combined_g'] = {
                'value': self.mean_combined_g,
                'percentile': percentile,
                'vs_field': quartile,
                'rank': rank,
                'field_size': len(field_g_force),
                'interpretation': 'grip_utilization'
            }

        # Full throttle percentage (higher is better)
        if field_full_throttle:
            percentile = 100 * sum(1 for x in field_full_throttle if x < self.full_throttle_pct) / len(field_full_throttle)

            # Determine rank
            sorted_throttle = sorted(field_full_throttle, reverse=True)
            rank = sum(1 for x in sorted_throttle if x > self.full_throttle_pct) + 1

            comparisons['full_throttle_pct'] = {
                'value': self.full_throttle_pct,
                'percentile': percentile,
                'vs_field': f"P{rank}",
                'rank': rank,
                'field_size': len(field_full_throttle),
                'interpretation': 'commitment'
            }

        return comparisons

    def get_training_recommendations(
        self,
        field_profiles: Optional[List['DriverProfile']] = None
    ) -> List[Dict]:
        """
        Get training recommendations based on profile gaps.

        Returns
        -------
        list of dict
            Recommendations with focus areas and exercises
        """
        recommendations = []

        if field_profiles:
            comparison = self.compare_to_field(field_profiles)

            # Check lift-off count
            if 'lift_off_count' in comparison:
                info = comparison['lift_off_count']
                if info['percentile'] < 50:  # Bottom half
                    recommendations.append({
                        'metric': 'lift_off_count',
                        'gap': f"Your lift-offs ({info['value']:.2f}/application) are {info['vs_field']}",
                        'focus': 'Traction management',
                        'exercise': 'Progressive throttle drills on skid pad - apply throttle slower on exit',
                        'priority': 'high' if info['percentile'] < 25 else 'medium'
                    })

            # Check G-force
            if 'mean_combined_g' in comparison:
                info = comparison['mean_combined_g']
                if info['percentile'] < 50:
                    recommendations.append({
                        'metric': 'mean_combined_g',
                        'gap': f"You're in {info['vs_field']} for grip utilization",
                        'focus': 'Grip confidence',
                        'exercise': 'Gradually increase entry speed in practice until you feel the limit',
                        'priority': 'high' if info['percentile'] < 25 else 'medium'
                    })

            # Check full throttle
            if 'full_throttle_pct' in comparison:
                info = comparison['full_throttle_pct']
                if info['percentile'] < 50:
                    recommendations.append({
                        'metric': 'full_throttle_pct',
                        'gap': f"You rank {info['vs_field']} of {info['field_size']} in full throttle time",
                        'focus': 'Commitment',
                        'exercise': 'Focus on getting to full throttle earlier on straights',
                        'priority': 'medium'
                    })

        return recommendations

    def __repr__(self) -> str:
        return (
            f"DriverProfile(#{self.vehicle_number}, "
            f"laps={self.laps_used}, "
            f"lift_offs={self.lift_off_count:.2f}, "
            f"G={self.mean_combined_g:.2f}, "
            f"full_thr={self.full_throttle_pct:.1f}%)"
        )


def build_field_profiles(
    telemetry: pd.DataFrame,
    laps: Optional[List[int]] = None
) -> List[DriverProfile]:
    """
    Build profiles for all drivers in the telemetry data.

    Parameters
    ----------
    telemetry : pd.DataFrame
        Telemetry data for all vehicles
    laps : list of int, optional
        Laps to use for profiles

    Returns
    -------
    list of DriverProfile
        Profiles for all drivers
    """
    vehicles = telemetry['vehicle_number'].dropna().unique()

    profiles = []
    for veh in vehicles:
        try:
            profile = DriverProfile.from_telemetry(telemetry, int(veh), laps)
            if profile.laps_used > 0:
                profiles.append(profile)
        except Exception:
            continue

    return profiles
