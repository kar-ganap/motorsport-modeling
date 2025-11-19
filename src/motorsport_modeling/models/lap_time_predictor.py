"""
Lap time prediction models.

This module contains:
- BaselineLapPredictor: Simple linear degradation model
- EnhancedLapPredictor: Gradient boosting with telemetry features
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Union
from pathlib import Path
import warnings
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import GradientBoostingRegressor
import joblib


class BaselineLapPredictor:
    """
    Simple linear degradation model for lap time prediction.

    Models lap time as:
        lap_time = baseline + degradation * lap + position_effect * position

    Fits per-driver parameters for interpretability.
    """

    def __init__(self):
        self.driver_models: Dict[int, Dict] = {}
        self.global_model = None
        self.is_fitted = False

    def fit(
        self,
        df: pd.DataFrame,
        target_col: str = 'lap_time',
        verbose: bool = True
    ) -> 'BaselineLapPredictor':
        """
        Fit the baseline model.

        Parameters
        ----------
        df : pd.DataFrame
            Training data with columns: vehicle_number, lap, lap_time
        target_col : str
            Name of target column
        verbose : bool
            Print progress

        Returns
        -------
        self
        """
        if verbose:
            print("Fitting baseline lap time predictor...")

        # Fit per-driver models
        for vehicle in df['vehicle_number'].unique():
            vehicle_data = df[df['vehicle_number'] == vehicle].copy()

            if len(vehicle_data) < 3:
                continue

            X = vehicle_data[['lap', 'position', 'laps_remaining']].values
            y = vehicle_data[target_col].values

            model = LinearRegression()
            model.fit(X, y)

            # Store model and stats
            predictions = model.predict(X)
            residuals = y - predictions
            rmse = np.sqrt(np.mean(residuals ** 2))

            self.driver_models[vehicle] = {
                'model': model,
                'baseline': model.intercept_,
                'lap_coef': model.coef_[0],  # Degradation per lap
                'position_coef': model.coef_[1],  # Effect of position
                'fuel_coef': model.coef_[2],  # Effect of remaining fuel
                'rmse': rmse,
                'n_samples': len(vehicle_data)
            }

        # Fit global model (for unseen drivers)
        X_global = df[['lap', 'position', 'laps_remaining']].values
        y_global = df[target_col].values

        self.global_model = LinearRegression()
        self.global_model.fit(X_global, y_global)

        self.is_fitted = True

        if verbose:
            print(f"Fitted models for {len(self.driver_models)} drivers")

            # Show average coefficients
            avg_degradation = np.mean([m['lap_coef'] for m in self.driver_models.values()])
            avg_position_effect = np.mean([m['position_coef'] for m in self.driver_models.values()])
            avg_rmse = np.mean([m['rmse'] for m in self.driver_models.values()])

            print(f"Average degradation per lap: {avg_degradation:.3f}s")
            print(f"Average position effect: {avg_position_effect:.3f}s per position")
            print(f"Average per-driver RMSE: {avg_rmse:.3f}s")

        return self

    def predict(
        self,
        df: pd.DataFrame,
        use_driver_models: bool = True
    ) -> np.ndarray:
        """
        Predict lap times.

        Parameters
        ----------
        df : pd.DataFrame
            Data with columns: vehicle_number, lap, position, laps_remaining
        use_driver_models : bool
            Use per-driver models if available

        Returns
        -------
        np.ndarray
            Predicted lap times
        """
        if not self.is_fitted:
            raise ValueError("Model not fitted. Call fit() first.")

        predictions = np.zeros(len(df))

        for i, (idx, row) in enumerate(df.iterrows()):
            vehicle = row['vehicle_number']
            X = np.array([[row['lap'], row['position'], row['laps_remaining']]])

            if use_driver_models and vehicle in self.driver_models:
                pred = self.driver_models[vehicle]['model'].predict(X)[0]
            else:
                pred = self.global_model.predict(X)[0]

            predictions[i] = pred

        return predictions

    def evaluate(
        self,
        df: pd.DataFrame,
        target_col: str = 'lap_time',
        verbose: bool = True
    ) -> Dict:
        """
        Evaluate model performance.

        Parameters
        ----------
        df : pd.DataFrame
            Test data
        target_col : str
            Name of target column
        verbose : bool
            Print results

        Returns
        -------
        dict
            Dictionary with evaluation metrics
        """
        predictions = self.predict(df)
        actuals = df[target_col].values

        residuals = actuals - predictions
        rmse = np.sqrt(np.mean(residuals ** 2))
        mae = np.mean(np.abs(residuals))

        # Position-weighted RMSE (penalize front-runner errors more)
        positions = df['position'].values
        weights = np.maximum(0.1, 1.0 - (positions - 1) * 0.05)
        weighted_rmse = np.sqrt(np.mean(weights * residuals ** 2))

        results = {
            'rmse': rmse,
            'mae': mae,
            'weighted_rmse': weighted_rmse,
            'mean_residual': np.mean(residuals),
            'std_residual': np.std(residuals)
        }

        if verbose:
            print(f"RMSE: {rmse:.3f}s")
            print(f"MAE: {mae:.3f}s")
            print(f"Position-weighted RMSE: {weighted_rmse:.3f}s")
            print(f"Mean residual: {results['mean_residual']:.3f}s")

        return results

    def get_driver_parameters(self) -> pd.DataFrame:
        """
        Get fitted parameters for all drivers.

        Returns
        -------
        pd.DataFrame
            DataFrame with driver parameters
        """
        if not self.is_fitted:
            raise ValueError("Model not fitted.")

        records = []
        for vehicle, params in self.driver_models.items():
            records.append({
                'vehicle_number': vehicle,
                'baseline': params['baseline'],
                'degradation_per_lap': params['lap_coef'],
                'position_effect': params['position_coef'],
                'fuel_effect': params['fuel_coef'],
                'rmse': params['rmse'],
                'n_samples': params['n_samples']
            })

        return pd.DataFrame(records).sort_values('rmse')

    def save(self, path: Union[str, Path]) -> None:
        """Save model to disk."""
        joblib.dump({
            'driver_models': self.driver_models,
            'global_model': self.global_model,
            'is_fitted': self.is_fitted
        }, path)

    @classmethod
    def load(cls, path: Union[str, Path]) -> 'BaselineLapPredictor':
        """Load model from disk."""
        data = joblib.load(path)
        model = cls()
        model.driver_models = data['driver_models']
        model.global_model = data['global_model']
        model.is_fitted = data['is_fitted']
        return model


class EnhancedLapPredictor:
    """
    Gradient boosting model with race context features.

    Uses features:
    - Position, gaps to ahead/behind/leader
    - Gap deltas (rate of change)
    - Race progress, fuel load estimate
    - Is fighting flag
    """

    def __init__(
        self,
        n_estimators: int = 100,
        max_depth: int = 5,
        learning_rate: float = 0.1,
        random_state: int = 42
    ):
        self.model = GradientBoostingRegressor(
            n_estimators=n_estimators,
            max_depth=max_depth,
            learning_rate=learning_rate,
            random_state=random_state
        )
        self.feature_cols: List[str] = []
        self.is_fitted = False

    def fit(
        self,
        df: pd.DataFrame,
        target_col: str = 'lap_time',
        feature_cols: Optional[List[str]] = None,
        verbose: bool = True
    ) -> 'EnhancedLapPredictor':
        """
        Fit the enhanced model.

        Parameters
        ----------
        df : pd.DataFrame
            Training data
        target_col : str
            Name of target column
        feature_cols : list, optional
            Feature columns to use. If None, uses defaults.
        verbose : bool
            Print progress

        Returns
        -------
        self
        """
        if feature_cols is None:
            feature_cols = [
                'lap',
                'position',
                'gap_to_leader',
                'gap_to_ahead',
                'gap_to_behind',
                'gap_delta_ahead',
                'gap_delta_behind',
                'race_progress',
                'fuel_load_estimate'
            ]

        # Check for missing columns
        missing = [c for c in feature_cols if c not in df.columns]
        if missing:
            raise ValueError(f"Missing columns: {missing}")

        self.feature_cols = feature_cols

        if verbose:
            print(f"Fitting enhanced lap time predictor...")
            print(f"Features: {len(feature_cols)}")
            print(f"Samples: {len(df)}")

        # Prepare features
        X = df[feature_cols].values
        y = df[target_col].values

        # Fit model (no scaling needed for tree-based models)
        self.model.fit(X, y)
        self.is_fitted = True

        if verbose:
            # Show feature importances
            importances = pd.DataFrame({
                'feature': feature_cols,
                'importance': self.model.feature_importances_
            }).sort_values('importance', ascending=False)

            print("\nTop 5 feature importances:")
            for _, row in importances.head().iterrows():
                print(f"  {row['feature']}: {row['importance']:.3f}")

        return self

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        """
        Predict lap times.

        Parameters
        ----------
        df : pd.DataFrame
            Data with required feature columns

        Returns
        -------
        np.ndarray
            Predicted lap times
        """
        if not self.is_fitted:
            raise ValueError("Model not fitted. Call fit() first.")

        X = df[self.feature_cols].values

        return self.model.predict(X)

    def evaluate(
        self,
        df: pd.DataFrame,
        target_col: str = 'lap_time',
        verbose: bool = True
    ) -> Dict:
        """
        Evaluate model performance.
        """
        predictions = self.predict(df)
        actuals = df[target_col].values

        residuals = actuals - predictions
        rmse = np.sqrt(np.mean(residuals ** 2))
        mae = np.mean(np.abs(residuals))

        # Position-weighted RMSE
        positions = df['position'].values
        weights = np.maximum(0.1, 1.0 - (positions - 1) * 0.05)
        weighted_rmse = np.sqrt(np.mean(weights * residuals ** 2))

        results = {
            'rmse': rmse,
            'mae': mae,
            'weighted_rmse': weighted_rmse,
            'mean_residual': np.mean(residuals),
            'std_residual': np.std(residuals)
        }

        if verbose:
            print(f"RMSE: {rmse:.3f}s")
            print(f"MAE: {mae:.3f}s")
            print(f"Position-weighted RMSE: {weighted_rmse:.3f}s")

        return results

    def get_feature_importances(self) -> pd.DataFrame:
        """
        Get feature importances.
        """
        if not self.is_fitted:
            raise ValueError("Model not fitted.")

        return pd.DataFrame({
            'feature': self.feature_cols,
            'importance': self.model.feature_importances_
        }).sort_values('importance', ascending=False)

    def save(self, path: Union[str, Path]) -> None:
        """Save model to disk."""
        joblib.dump({
            'model': self.model,
            'feature_cols': self.feature_cols,
            'is_fitted': self.is_fitted
        }, path)

    @classmethod
    def load(cls, path: Union[str, Path]) -> 'EnhancedLapPredictor':
        """Load model from disk."""
        data = joblib.load(path)
        predictor = cls()
        predictor.model = data['model']
        predictor.feature_cols = data['feature_cols']
        predictor.is_fitted = data['is_fitted']
        return predictor


def predict_race_winner(
    predictions: Dict[int, float],
    current_cumulative: Dict[int, float]
) -> Tuple[int, Dict[int, float]]:
    """
    Predict race winner based on predicted remaining lap times.

    Parameters
    ----------
    predictions : dict
        {vehicle_number: predicted_remaining_time}
    current_cumulative : dict
        {vehicle_number: current_cumulative_time}

    Returns
    -------
    tuple
        (predicted_winner, {vehicle: predicted_total_time})
    """
    totals = {}
    for vehicle in predictions:
        if vehicle in current_cumulative:
            totals[vehicle] = current_cumulative[vehicle] + predictions[vehicle]
        else:
            totals[vehicle] = predictions[vehicle]

    winner = min(totals, key=totals.get)
    return winner, totals


def compute_winner_accuracy(
    model,
    df: pd.DataFrame,
    from_lap: int,
    total_laps: int = 26,
    verbose: bool = False
) -> Dict:
    """
    Compute winner prediction accuracy from a given lap.

    Parameters
    ----------
    model : BaselineLapPredictor or EnhancedLapPredictor
        Fitted model
    df : pd.DataFrame
        Complete race data
    from_lap : int
        Lap to make prediction from
    total_laps : int
        Total laps in race
    verbose : bool
        Print details

    Returns
    -------
    dict
        {correct: bool, predicted_winner: int, actual_winner: int, ...}
    """
    # Get remaining laps data
    remaining = df[df['lap'] > from_lap].copy()

    if len(remaining) == 0:
        return {'error': f'No data after lap {from_lap}'}

    # Predict remaining lap times
    predictions = model.predict(remaining)
    remaining['predicted_lap_time'] = predictions

    # Sum predicted times per driver
    predicted_totals = remaining.groupby('vehicle_number')['predicted_lap_time'].sum()
    actual_totals = remaining.groupby('vehicle_number')['lap_time'].sum()

    # Get current cumulative times at from_lap
    current = df[df['lap'] == from_lap]
    current_cum = dict(zip(current['vehicle_number'], current['cumulative_time']))

    # Final totals
    pred_final = {v: current_cum.get(v, 0) + predicted_totals[v]
                  for v in predicted_totals.index}
    actual_final = {v: current_cum.get(v, 0) + actual_totals[v]
                    for v in actual_totals.index}

    predicted_winner = min(pred_final, key=pred_final.get)
    actual_winner = min(actual_final, key=actual_final.get)

    result = {
        'from_lap': from_lap,
        'correct': predicted_winner == actual_winner,
        'predicted_winner': predicted_winner,
        'actual_winner': actual_winner,
        'predicted_margin': sorted(pred_final.values())[1] - min(pred_final.values()) if len(pred_final) > 1 else 0,
        'actual_margin': sorted(actual_final.values())[1] - min(actual_final.values()) if len(actual_final) > 1 else 0
    }

    if verbose:
        status = "✓" if result['correct'] else "✗"
        print(f"From lap {from_lap}: {status} Predicted {predicted_winner}, Actual {actual_winner}")

    return result


# =============================================================================
# REGIME-AWARE RELATIVE PERFORMANCE PREDICTOR
# =============================================================================

from dataclasses import dataclass
from sklearn.ensemble import RandomForestClassifier


@dataclass
class PredictionResult:
    """Single prediction with uncertainty."""
    vehicle_number: int
    lap: int
    predicted_relative: float  # seconds vs field median
    uncertainty: float  # standard deviation
    regime: str  # 'green', 'yellow', 'restart'
    confidence: str  # 'high', 'medium', 'low'

    def format_for_display(self) -> str:
        """Format prediction for dashboard display."""
        sign = '+' if self.predicted_relative >= 0 else ''
        return (
            f"#{self.vehicle_number} Lap {self.lap}: "
            f"{sign}{self.predicted_relative:.2f}s ± {self.uncertainty:.1f}s "
            f"({self.confidence} confidence)"
        )


class RelativePerformancePredictor:
    """
    Regime-aware lap time predictor using relative performance.

    Predicts relative performance (lap_time - field_median) with
    uncertainty estimates based on race regime detection.

    This is the recommended predictor for real-time use as it:
    - Normalizes out race events (yellow flags, restarts)
    - Provides uncertainty estimates
    - Has validated RMSE of ~1.9s for green flag laps
    """

    def __init__(self, alpha: float = 0.3):
        """
        Initialize predictor.

        Parameters
        ----------
        alpha : float
            Weight on previous lap (vs driver mean). Default 0.3.
            Higher = more reactive to recent performance.
        """
        self.alpha = alpha
        self.driver_means: Dict[int, float] = {}
        self.driver_prev_relative: Dict[int, float] = {}
        self.event_detector: Optional[RandomForestClassifier] = None
        self.event_feature_cols: List[str] = []
        self.field_baseline: float = 0.0
        self.is_fitted = False

        # Regime-specific uncertainties (from validation)
        self.regime_uncertainty = {
            'green': 1.9,
            'yellow': 2.5,
            'restart': 7.0
        }

    def fit(self, data: pd.DataFrame, verbose: bool = False) -> 'RelativePerformancePredictor':
        """
        Fit predictor on historical race data.

        Parameters
        ----------
        data : pd.DataFrame
            Race data with columns: vehicle_number, lap, lap_time,
            gap_to_ahead, is_fighting, position, is_under_yellow (optional)
        verbose : bool
            Print fitting progress

        Returns
        -------
        self
        """
        df = data.copy()

        # Compute relative performance
        field_median = df.groupby('lap')['lap_time'].median()
        df['field_median'] = df['lap'].map(field_median)
        df['relative_time'] = df['lap_time'] - df['field_median']

        # Store baseline
        self.field_baseline = field_median.median()

        # Compute driver means
        self.driver_means = df.groupby('vehicle_number')['relative_time'].mean().to_dict()

        # Store last relative time per driver
        last_lap = df.groupby('vehicle_number')['lap'].max()
        for veh in df['vehicle_number'].unique():
            max_lap = last_lap[veh]
            last_row = df[(df['vehicle_number'] == veh) & (df['lap'] == max_lap)]
            if len(last_row) > 0:
                self.driver_prev_relative[veh] = last_row['relative_time'].iloc[0]

        # Train event detector if we have flag data
        if 'is_under_yellow' in df.columns:
            self._fit_event_detector(df, verbose)

        self.is_fitted = True

        if verbose:
            print(f"Fitted on {len(df)} samples, {len(self.driver_means)} drivers")
            print(f"Field baseline: {self.field_baseline:.2f}s")

        return self

    def _fit_event_detector(self, df: pd.DataFrame, verbose: bool = False):
        """Train event detector on historical data."""
        # Compute per-lap features
        lap_features = df.groupby('lap').agg({
            'lap_time': ['median', 'std'],
            'gap_to_ahead': ['mean', 'std'],
            'is_fighting': 'sum',
            'position': 'count'
        }).reset_index()

        lap_features.columns = [
            'lap', 'field_median', 'lap_time_std',
            'avg_gap', 'gap_std', 'fighting_count', 'car_count'
        ]

        # Add position churn
        sorted_df = df.sort_values(['vehicle_number', 'lap'])
        sorted_df['position_change'] = sorted_df.groupby('vehicle_number')['position'].diff().abs()
        churn = sorted_df.groupby('lap')['position_change'].sum().reset_index()
        churn.columns = ['lap', 'position_churn']
        lap_features = lap_features.merge(churn, on='lap', how='left')
        lap_features['position_churn'] = lap_features['position_churn'].fillna(0)

        # Add lap time spread
        lap_features['lap_time_spread'] = (
            df.groupby('lap')['lap_time'].max().values -
            df.groupby('lap')['lap_time'].min().values
        )

        # Get yellow flag status
        yellow = df.groupby('lap')['is_under_yellow'].max().reset_index()
        lap_features = lap_features.merge(yellow, on='lap', how='left')

        # Target: yellow on next lap
        lap_features['next_yellow'] = lap_features['is_under_yellow'].shift(-1).fillna(0).astype(int)

        # Features
        self.event_feature_cols = [
            'avg_gap', 'gap_std', 'fighting_count',
            'position_churn', 'lap_time_std', 'lap_time_spread'
        ]

        valid = lap_features.dropna(subset=self.event_feature_cols + ['next_yellow'])

        if len(valid) >= 5:
            X = valid[self.event_feature_cols].values
            y = valid['next_yellow'].values

            self.event_detector = RandomForestClassifier(
                n_estimators=50, max_depth=3, random_state=42
            )
            self.event_detector.fit(X, y)

            if verbose:
                acc = (self.event_detector.predict(X) == y).mean()
                print(f"Event detector accuracy: {acc:.1%}")

    def predict(
        self,
        data: pd.DataFrame,
        return_dataframe: bool = False
    ) -> Union[List[PredictionResult], pd.DataFrame]:
        """
        Predict relative performance for each driver-lap.

        Parameters
        ----------
        data : pd.DataFrame
            Data to predict on (needs vehicle_number, lap, and features
            for event detection)
        return_dataframe : bool
            Return as DataFrame instead of list

        Returns
        -------
        List[PredictionResult] or pd.DataFrame
        """
        if not self.is_fitted:
            raise ValueError("Predictor not fitted. Call fit() first.")

        df = data.copy()

        # Detect current regime
        regime = self._detect_regime(df)
        yellow_prob = self._predict_yellow_probability(df)

        # Set uncertainty based on regime and yellow probability
        base_uncertainty = self.regime_uncertainty[regime]
        if yellow_prob > 0.5:
            base_uncertainty *= 1.5  # Increase uncertainty when yellow likely

        # Predict for each driver
        results = []

        for veh in df['vehicle_number'].unique():
            veh_data = df[df['vehicle_number'] == veh].sort_values('lap')

            for _, row in veh_data.iterrows():
                lap = int(row['lap'])

                # Get driver mean (or 0 for unknown driver)
                driver_mean = self.driver_means.get(veh, 0)

                # Get previous relative (or driver mean)
                prev_rel = self.driver_prev_relative.get(veh, driver_mean)

                # Weighted prediction
                predicted = self.alpha * prev_rel + (1 - self.alpha) * driver_mean

                # Determine confidence
                if regime == 'green' and yellow_prob < 0.3:
                    confidence = 'high'
                elif regime == 'restart' or yellow_prob > 0.7:
                    confidence = 'low'
                else:
                    confidence = 'medium'

                results.append(PredictionResult(
                    vehicle_number=int(veh),
                    lap=lap,
                    predicted_relative=predicted,
                    uncertainty=base_uncertainty,
                    regime=regime,
                    confidence=confidence
                ))

                # Update previous relative for next prediction
                self.driver_prev_relative[veh] = predicted

        if return_dataframe:
            return pd.DataFrame([
                {
                    'vehicle_number': r.vehicle_number,
                    'lap': r.lap,
                    'predicted_relative': r.predicted_relative,
                    'uncertainty': r.uncertainty,
                    'regime': r.regime,
                    'confidence': r.confidence
                }
                for r in results
            ])

        return results

    def update(self, vehicle_number: int, actual_relative: float):
        """
        Update driver state with actual result (for real-time use).

        Parameters
        ----------
        vehicle_number : int
            Driver's vehicle number
        actual_relative : float
            Actual relative time for completed lap
        """
        self.driver_prev_relative[vehicle_number] = actual_relative

        # Update running mean (exponential smoothing)
        if vehicle_number in self.driver_means:
            old_mean = self.driver_means[vehicle_number]
            self.driver_means[vehicle_number] = 0.9 * old_mean + 0.1 * actual_relative

    def _detect_regime(self, data: pd.DataFrame) -> str:
        """Detect current race regime from data."""
        if len(data) == 0:
            return 'green'

        # Check for yellow flag
        if 'is_under_yellow' in data.columns:
            if data['is_under_yellow'].max() == 1:
                return 'yellow'

        # Check for restart pattern (high lap time deviation)
        median_time = data['lap_time'].median()
        if median_time > self.field_baseline + 20:
            return 'restart'
        elif median_time > self.field_baseline + 5:
            return 'yellow'

        return 'green'

    def _predict_yellow_probability(self, data: pd.DataFrame) -> float:
        """Predict probability of yellow flag on next lap."""
        if self.event_detector is None or len(data) == 0:
            return 0.0

        try:
            # Compute features for current lap
            features = {
                'avg_gap': data['gap_to_ahead'].mean(),
                'gap_std': data['gap_to_ahead'].std(),
                'fighting_count': data['is_fighting'].sum() if 'is_fighting' in data.columns else 0,
                'position_churn': 0,  # Would need previous lap
                'lap_time_std': data['lap_time'].std(),
                'lap_time_spread': data['lap_time'].max() - data['lap_time'].min()
            }

            X = np.array([[features[col] for col in self.event_feature_cols]])
            prob = self.event_detector.predict_proba(X)[0, 1]
            return prob

        except Exception:
            return 0.0

    def get_field_predictions(
        self,
        data: pd.DataFrame,
        lap: int
    ) -> pd.DataFrame:
        """
        Get predictions for all drivers on a specific lap.

        Returns DataFrame sorted by predicted performance (fastest first).
        """
        lap_data = data[data['lap'] == lap]
        predictions = self.predict(lap_data, return_dataframe=True)

        return predictions.sort_values('predicted_relative')


def create_relative_predictor(
    race_data: pd.DataFrame,
    alpha: float = 0.3,
    verbose: bool = False
) -> RelativePerformancePredictor:
    """
    Convenience function to create and fit relative performance predictor.

    Parameters
    ----------
    race_data : pd.DataFrame
        Historical race data
    alpha : float
        Weight on previous lap
    verbose : bool
        Print progress

    Returns
    -------
    RelativePerformancePredictor
        Fitted predictor
    """
    predictor = RelativePerformancePredictor(alpha=alpha)
    predictor.fit(race_data, verbose=verbose)
    return predictor
