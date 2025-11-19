"""
Race outcome prediction and counterfactual analysis.

Provides:
1. Position prediction based on pace deltas
2. Winner/podium prediction from any point in race
3. Counterfactual analysis - "how could runner-up have won?"
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class PositionPrediction:
    """Prediction for a single driver's final position."""
    vehicle_number: int
    current_position: int
    predicted_position: int
    confidence: float  # 0-1
    overtakes_predicted: int
    laps_to_overtake: Dict[int, int]  # {opponent: laps_needed}


@dataclass
class CounterfactualResult:
    """Result of counterfactual analysis."""
    vehicle_number: int
    actual_position: int
    actual_gap_to_winner: float
    time_lost_to_degradation: float
    potential_gain_per_lap: float
    total_potential_gain: float
    would_have_won: bool
    narrative: str


class RacePredictor:
    """
    Predicts race outcomes using pace delta model.

    Key insight: overtake happens when:
        gap / pace_delta < remaining_laps
    """

    def __init__(self):
        self.driver_paces: Dict[int, float] = {}  # vehicle -> avg relative time
        self.driver_pace_window: int = 5  # laps to compute recent pace

    def fit(self, data: pd.DataFrame, verbose: bool = False):
        """
        Compute driver pace profiles from race data.

        Parameters
        ----------
        data : pd.DataFrame
            Race data with relative_time computed
        """
        # Compute relative time if not present
        if 'relative_time' not in data.columns:
            field_median = data.groupby('lap')['lap_time'].median()
            data = data.copy()
            data['field_median'] = data['lap'].map(field_median)
            data['relative_time'] = data['lap_time'] - data['field_median']

        # Compute average pace per driver
        self.driver_paces = data.groupby('vehicle_number')['relative_time'].mean().to_dict()

        if verbose:
            print(f"Computed pace for {len(self.driver_paces)} drivers")
            fastest = min(self.driver_paces, key=self.driver_paces.get)
            slowest = max(self.driver_paces, key=self.driver_paces.get)
            print(f"Fastest: #{fastest} ({self.driver_paces[fastest]:+.2f}s)")
            print(f"Slowest: #{slowest} ({self.driver_paces[slowest]:+.2f}s)")

    def predict_positions(
        self,
        data: pd.DataFrame,
        from_lap: int,
        total_laps: int = 26
    ) -> List[PositionPrediction]:
        """
        Predict final positions from a given lap.

        Uses pace delta model:
        - For each pair of adjacent drivers, compute pace delta
        - If gap / |pace_delta| < remaining_laps, predict overtake

        Parameters
        ----------
        data : pd.DataFrame
            Race data up to from_lap
        from_lap : int
            Current lap to predict from
        total_laps : int
            Total laps in race

        Returns
        -------
        List[PositionPrediction]
        """
        remaining = total_laps - from_lap

        # Get current state at from_lap
        current = data[data['lap'] == from_lap].sort_values('position')

        if len(current) == 0:
            return []

        # Compute recent pace for each driver (last N laps)
        recent_laps = data[
            (data['lap'] > from_lap - self.driver_pace_window) &
            (data['lap'] <= from_lap)
        ]

        if 'relative_time' not in recent_laps.columns:
            field_median = recent_laps.groupby('lap')['lap_time'].median()
            recent_laps = recent_laps.copy()
            recent_laps['field_median'] = recent_laps['lap'].map(field_median)
            recent_laps['relative_time'] = recent_laps['lap_time'] - recent_laps['field_median']

        recent_pace = recent_laps.groupby('vehicle_number')['relative_time'].mean().to_dict()

        # Build prediction for each driver
        predictions = []
        positions = current['position'].values
        vehicles = current['vehicle_number'].values
        gaps = current['gap_to_ahead'].values

        # Simulate overtakes
        predicted_positions = {veh: int(pos) for veh, pos in zip(vehicles, positions)}
        overtakes = {veh: {} for veh in vehicles}

        for i in range(len(vehicles)):
            veh = vehicles[i]
            my_pace = recent_pace.get(veh, self.driver_paces.get(veh, 0))

            # Check if can overtake car ahead
            if i > 0:
                ahead_veh = vehicles[i-1]
                ahead_pace = recent_pace.get(ahead_veh, self.driver_paces.get(ahead_veh, 0))
                pace_delta = my_pace - ahead_pace  # negative = I'm faster

                if pace_delta < -0.1:  # I'm faster by at least 0.1s/lap
                    gap = gaps[i]
                    laps_to_catch = gap / abs(pace_delta) if abs(pace_delta) > 0.01 else float('inf')

                    if laps_to_catch < remaining:
                        overtakes[veh][ahead_veh] = int(np.ceil(laps_to_catch))

            # Check if car behind will overtake me
            if i < len(vehicles) - 1:
                behind_veh = vehicles[i+1]
                behind_pace = recent_pace.get(behind_veh, self.driver_paces.get(behind_veh, 0))
                pace_delta = behind_pace - my_pace  # negative = they're faster

                if pace_delta < -0.1:
                    gap = gaps[i+1] if i+1 < len(gaps) else 0
                    laps_to_catch = gap / abs(pace_delta) if abs(pace_delta) > 0.01 else float('inf')

                    if laps_to_catch < remaining:
                        overtakes[behind_veh][veh] = int(np.ceil(laps_to_catch))

        # Apply overtakes to predict final positions
        for veh in vehicles:
            n_overtakes = len(overtakes[veh])
            current_pos = predicted_positions[veh]
            predicted_pos = max(1, current_pos - n_overtakes)

            # Confidence based on pace consistency
            veh_laps = recent_laps[recent_laps['vehicle_number'] == veh]['relative_time']
            if len(veh_laps) > 1:
                pace_std = veh_laps.std()
                confidence = max(0.3, 1.0 - pace_std / 3.0)  # Lower std = higher confidence
            else:
                confidence = 0.5

            predictions.append(PositionPrediction(
                vehicle_number=int(veh),
                current_position=int(current_pos),
                predicted_position=int(predicted_pos),
                confidence=confidence,
                overtakes_predicted=n_overtakes,
                laps_to_overtake=overtakes[veh]
            ))

        return sorted(predictions, key=lambda x: x.predicted_position)

    def predict_winner(
        self,
        data: pd.DataFrame,
        from_lap: int,
        total_laps: int = 26
    ) -> Tuple[int, float]:
        """
        Predict race winner from given lap.

        Returns
        -------
        tuple
            (predicted_winner_vehicle, confidence)
        """
        predictions = self.predict_positions(data, from_lap, total_laps)

        if not predictions:
            return None, 0.0

        # Winner is P1 prediction
        winner_pred = predictions[0]
        return winner_pred.vehicle_number, winner_pred.confidence

    def predict_podium(
        self,
        data: pd.DataFrame,
        from_lap: int,
        total_laps: int = 26
    ) -> List[Tuple[int, float]]:
        """
        Predict top 3 finishers.

        Returns
        -------
        list
            [(vehicle, confidence), ...] for P1, P2, P3
        """
        predictions = self.predict_positions(data, from_lap, total_laps)

        podium = []
        for pred in predictions[:3]:
            podium.append((pred.vehicle_number, pred.confidence))

        return podium


class CounterfactualAnalyzer:
    """
    Analyzes "what if" scenarios for race outcomes.

    Key question: "How could the runner-up have won?"
    """

    def __init__(self):
        self.technique_impact = {
            'brake_cv': 0.15,  # seconds per lap improvement
            'lift_off_count': 0.08,
            'coasting_pct': 0.10,
            'throttle_smoothness': 0.12
        }

    def analyze_runner_up(
        self,
        race_data: pd.DataFrame,
        technique_data: Optional[pd.DataFrame] = None,
        verbose: bool = True
    ) -> CounterfactualResult:
        """
        Analyze how runner-up could have won.

        Parameters
        ----------
        race_data : pd.DataFrame
            Complete race data with lap times
        technique_data : pd.DataFrame, optional
            Per-lap technique metrics
        verbose : bool
            Print analysis

        Returns
        -------
        CounterfactualResult
        """
        # Get final standings using position column (authoritative)
        final_lap = race_data['lap'].max()
        final_state = race_data[race_data['lap'] == final_lap].sort_values('position')

        if len(final_state) < 2:
            return None

        winner = final_state.iloc[0]
        runner_up = final_state.iloc[1]

        winner_veh = int(winner['vehicle_number'])
        runner_up_veh = int(runner_up['vehicle_number'])

        # Gap to winner - use gap_to_ahead for runner-up
        # This is the actual gap when crossing the finish line
        gap = runner_up['gap_to_ahead']

        # Fallback to timestamp difference if gap_to_ahead not available
        if pd.isna(gap) or gap == 0:
            # Use timestamp difference
            if 'timestamp' in final_state.columns:
                gap = (runner_up['timestamp'] - winner['timestamp']).total_seconds()
            else:
                # Last resort: cumulative time difference
                gap = runner_up['cumulative_time'] - winner['cumulative_time']

        if verbose:
            print(f"Winner: #{winner_veh}")
            print(f"Runner-up: #{runner_up_veh}")
            print(f"Gap: {gap:.2f}s")

        # Analyze degradation
        runner_up_laps = race_data[race_data['vehicle_number'] == runner_up_veh].sort_values('lap')

        # Baseline: laps 3-5
        baseline_laps = runner_up_laps[runner_up_laps['lap'].between(3, 5)]
        # Late race: laps 20-22 (or last available)
        late_laps = runner_up_laps[runner_up_laps['lap'] >= 20]

        if len(baseline_laps) == 0 or len(late_laps) == 0:
            baseline_pace = runner_up_laps['lap_time'].mean()
            late_pace = baseline_pace
        else:
            baseline_pace = baseline_laps['lap_time'].mean()
            late_pace = late_laps['lap_time'].mean()

        degradation = late_pace - baseline_pace

        # Estimate time lost to degradation
        # Assume degradation is linear over race
        degradation_per_lap = degradation / (final_lap - 5) if final_lap > 5 else 0
        # Time lost = sum of degradation over all laps (triangular)
        time_lost = degradation_per_lap * (final_lap * (final_lap - 1) / 2 - 15)  # Simplified
        time_lost = max(0, time_lost)

        # Potential improvement if technique maintained
        if technique_data is not None:
            potential = self._compute_technique_potential(
                technique_data, runner_up_veh, final_lap
            )
        else:
            # Estimate 0.1-0.2s per lap improvement possible
            potential = 0.15 * final_lap

        # Would they have won?
        would_have_won = potential > gap

        # Build narrative
        narrative = self._build_narrative(
            runner_up_veh, winner_veh, gap, degradation,
            time_lost, potential, would_have_won
        )

        if verbose:
            print(f"\n{narrative}")

        return CounterfactualResult(
            vehicle_number=runner_up_veh,
            actual_position=2,
            actual_gap_to_winner=gap,
            time_lost_to_degradation=time_lost,
            potential_gain_per_lap=potential / final_lap,
            total_potential_gain=potential,
            would_have_won=would_have_won,
            narrative=narrative
        )

    def _compute_technique_potential(
        self,
        technique_data: pd.DataFrame,
        vehicle: int,
        total_laps: int
    ) -> float:
        """Compute potential time gain from technique improvements."""
        veh_data = technique_data[technique_data['vehicle_number'] == vehicle]

        if len(veh_data) == 0:
            return 0.15 * total_laps

        # Compare baseline (early) vs late race
        early = veh_data[veh_data['lap'] <= 5]
        late = veh_data[veh_data['lap'] >= 20]

        total_potential = 0

        for metric, impact in self.technique_impact.items():
            if metric in veh_data.columns:
                if len(early) > 0 and len(late) > 0:
                    early_val = early[metric].mean()
                    late_val = late[metric].mean()

                    # Degradation = how much worse late race is
                    if metric in ['brake_cv', 'lift_off_count']:
                        # Higher is worse
                        degradation_pct = (late_val - early_val) / early_val if early_val > 0 else 0
                    else:
                        # Lower is worse
                        degradation_pct = (early_val - late_val) / early_val if early_val > 0 else 0

                    if degradation_pct > 0:
                        # Potential gain per lap from maintaining baseline
                        gain_per_lap = impact * degradation_pct
                        # Apply to last N laps where degradation occurred
                        n_degraded_laps = total_laps - 10
                        total_potential += gain_per_lap * n_degraded_laps

        return total_potential

    def _build_narrative(
        self,
        runner_up: int,
        winner: int,
        gap: float,
        degradation: float,
        time_lost: float,
        potential: float,
        would_have_won: bool
    ) -> str:
        """Build human-readable narrative for counterfactual."""

        lines = [
            f"COUNTERFACTUAL ANALYSIS: How #{runner_up} could have won",
            "=" * 50
        ]

        lines.append(f"\nFinal gap to winner #{winner}: {gap:.2f}s")

        if degradation > 0.5:
            lines.append(f"\nLate-race degradation: {degradation:.2f}s slower than baseline")
            lines.append(f"Estimated time lost to degradation: {time_lost:.1f}s")
        else:
            lines.append(f"\nPace was consistent throughout (degradation: {degradation:.2f}s)")

        lines.append(f"\nPotential time gain from technique optimization: {potential:.1f}s")
        lines.append(f"  ({potential/26:.2f}s per lap on average)")

        if would_have_won:
            margin = potential - gap
            lines.append(f"\nVERDICT: Could have WON by {margin:.2f}s")
            lines.append("\nKey improvements needed:")
            lines.append("  - Maintain baseline braking smoothness")
            lines.append("  - Reduce late-race throttle lift-offs")
            lines.append("  - Optimize trail braking in slow corners")
        else:
            shortfall = gap - potential
            lines.append(f"\nVERDICT: Would still have lost by {shortfall:.2f}s")
            lines.append(f"\nWinner #{winner} was genuinely faster.")

        return "\n".join(lines)

    def compare_drivers(
        self,
        race_data: pd.DataFrame,
        driver_a: int,
        driver_b: int
    ) -> Dict:
        """
        Compare pace profiles of two drivers.

        Returns dict with:
        - pace_difference: avg lap time difference
        - consistent_advantage: whether one always faster
        - crossover_laps: laps where relative pace changed
        """
        a_data = race_data[race_data['vehicle_number'] == driver_a].sort_values('lap')
        b_data = race_data[race_data['vehicle_number'] == driver_b].sort_values('lap')

        # Merge on lap
        merged = a_data[['lap', 'lap_time']].merge(
            b_data[['lap', 'lap_time']],
            on='lap',
            suffixes=('_a', '_b')
        )

        merged['delta'] = merged['lap_time_a'] - merged['lap_time_b']

        return {
            'pace_difference': merged['delta'].mean(),
            'a_faster_laps': (merged['delta'] < 0).sum(),
            'b_faster_laps': (merged['delta'] > 0).sum(),
            'crossover_laps': merged[merged['delta'].diff().abs() > 0.5]['lap'].tolist(),
            'largest_gap': merged['delta'].abs().max()
        }


def validate_position_prediction(
    data: pd.DataFrame,
    from_laps: List[int] = [10, 15, 20],
    verbose: bool = True
) -> Dict:
    """
    Validate position prediction accuracy.

    Parameters
    ----------
    data : pd.DataFrame
        Complete race data
    from_laps : list
        Laps to test prediction from
    verbose : bool
        Print results

    Returns
    -------
    dict
        {from_lap: {accuracy metrics}}
    """
    total_laps = int(data['lap'].max())

    # Get actual final positions using position column (authoritative)
    final = data[data['lap'] == total_laps].sort_values('position')
    actual_positions = {int(row['vehicle_number']): int(row['position'])
                        for _, row in final.iterrows()}

    # Get winner and podium from sorted positions
    sorted_by_pos = sorted(actual_positions.items(), key=lambda x: x[1])
    actual_winner = sorted_by_pos[0][0]
    actual_podium = set([v for v, p in sorted_by_pos[:3]])

    predictor = RacePredictor()
    predictor.fit(data, verbose=False)

    results = {}

    for from_lap in from_laps:
        if from_lap >= total_laps:
            continue

        predictions = predictor.predict_positions(data, from_lap, total_laps)

        if not predictions:
            continue

        # Compute metrics
        position_errors = []
        for pred in predictions:
            actual_pos = actual_positions.get(pred.vehicle_number, 99)
            error = abs(pred.predicted_position - actual_pos)
            position_errors.append(error)

        mean_error = np.mean(position_errors)

        # Winner correct?
        pred_winner = predictions[0].vehicle_number
        winner_correct = pred_winner == actual_winner

        # Podium correct (any order)?
        pred_podium = set([p.vehicle_number for p in predictions[:3]])
        podium_correct = pred_podium == actual_podium

        # Top-3 accuracy (correct position)
        top3_correct = sum(
            1 for p in predictions[:3]
            if actual_positions.get(p.vehicle_number) == p.predicted_position
        )

        results[from_lap] = {
            'mean_position_error': mean_error,
            'winner_correct': winner_correct,
            'podium_correct': podium_correct,
            'top3_exact': top3_correct,
            'predicted_winner': pred_winner,
            'actual_winner': actual_winner
        }

        if verbose:
            status = "CORRECT" if winner_correct else "WRONG"
            print(f"From lap {from_lap}:")
            print(f"  Mean position error: {mean_error:.1f}")
            print(f"  Winner: {status} (predicted #{pred_winner}, actual #{actual_winner})")
            print(f"  Podium exact: {top3_correct}/3")

    return results
