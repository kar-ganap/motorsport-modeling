"""
Simple Linear Lap Time Model for Counterfactual Analysis

Model: lap_time_delta ~ degradation_rate + consistency + traffic_laps

Where lap_time_delta = avg_lap_time - baseline_pace (deviation from early-stint pace)
This removes multicollinearity by modeling only the controllable deviation from baseline.
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional
from dataclasses import dataclass
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import cross_val_score, LeaveOneOut
from sklearn.metrics import r2_score, mean_absolute_error


@dataclass
class ModelCoefficients:
    """Interpretable model coefficients showing impact of each factor on deviation from baseline."""
    degradation_impact: float  # s/lap deviation per 0.001 s/lap degradation rate
    consistency_impact: float  # s/lap deviation per 0.1s std dev
    traffic_impact: float      # s/lap cost per lap in traffic
    intercept: float           # Expected deviation with zero controllable factors

    def summary(self) -> str:
        """Generate human-readable summary of coefficients."""
        return f"""
Model Coefficients (Impact on Deviation from Baseline Pace):
  Degradation: {self.degradation_impact:.4f} s/lap per 0.001 s/lap degradation rate
  Consistency: {self.consistency_impact:.4f} s/lap per 0.1s std dev
  Traffic: {self.traffic_impact:.4f} s/lap per lap in traffic
  Intercept: {self.intercept:.3f} s (baseline deviation)

Interpretation:
  - Reducing degradation by 0.01 s/lap → {abs(self.degradation_impact * 10):.3f}s faster avg lap
  - Improving consistency by 0.1s → {abs(self.consistency_impact):.3f}s faster avg lap
  - One fewer lap in traffic → {abs(self.traffic_impact):.3f}s faster avg lap
"""


@dataclass
class ModelValidation:
    """Validation metrics for model quality."""
    r2_score: float                    # R² on training data
    cv_r2_mean: float                  # Mean R² from cross-validation
    cv_r2_std: float                   # Std dev of CV R²
    mae: float                         # Mean absolute error (seconds)
    sanity_checks_passed: bool         # Did coefficients pass sanity checks?
    sanity_check_results: Dict[str, bool]


class LapTimeModel:
    """
    Simple linear model to predict deviation from baseline pace.

    Model equation:
        lap_time_delta = β₀ + β₁*degradation + β₂*consistency + β₃*traffic

    Where:
        - lap_time_delta: deviation from baseline (avg_lap_time - baseline_pace)
        - degradation: tire degradation rate (s/lap)
        - consistency: lap time std dev (s)
        - traffic: number of laps in traffic

    By removing car_performance and modeling deviation, we eliminate multicollinearity
    and focus on the controllable factors that cause pace deterioration.
    """

    def __init__(self):
        self.model = LinearRegression()
        self.feature_names = [
            'controllable_degradation_rate',
            'controllable_consistency',
            'controllable_traffic_laps',
        ]
        self.coefficients: Optional[ModelCoefficients] = None
        self.validation: Optional[ModelValidation] = None
        self.is_fitted = False

    def fit(self, features_df: pd.DataFrame, verbose: bool = True) -> 'LapTimeModel':
        """
        Fit the model on feature data.

        Args:
            features_df: DataFrame from extract_race_features()
            verbose: Print training summary

        Returns:
            Self for method chaining
        """
        # Prepare features and target (deviation from baseline)
        X = features_df[self.feature_names].copy()
        y = features_df['lap_time_delta'].copy()

        # Remove NaN rows
        mask = ~(X.isna().any(axis=1) | y.isna())
        X = X[mask]
        y = y[mask]

        if len(X) < 10:
            raise ValueError(f"Insufficient data: only {len(X)} valid samples")

        # Fit model
        self.model.fit(X, y)
        self.is_fitted = True

        # Store coefficients
        coefs = self.model.coef_
        self.coefficients = ModelCoefficients(
            degradation_impact=coefs[0] * 0.001,  # Scale to 0.001 s/lap
            consistency_impact=coefs[1] * 0.1,    # Scale to 0.1s std dev
            traffic_impact=coefs[2],              # Already per lap
            intercept=self.model.intercept_
        )

        # Validation
        self.validation = self._validate(X, y)

        if verbose:
            print(self.coefficients.summary())
            print(f"\nModel Performance:")
            print(f"  R² Score: {self.validation.r2_score:.3f}")
            print(f"  Cross-Val R² (LOO): {self.validation.cv_r2_mean:.3f} ± {self.validation.cv_r2_std:.3f}")
            print(f"  Mean Absolute Error: {self.validation.mae:.3f}s")
            print(f"  Sanity Checks: {'✓ PASSED' if self.validation.sanity_checks_passed else '✗ FAILED'}")

            if not self.validation.sanity_checks_passed:
                print("\n  Failed checks:")
                for check, passed in self.validation.sanity_check_results.items():
                    if not passed:
                        print(f"    - {check}")

        return self

    def predict(self, features_df: pd.DataFrame) -> np.ndarray:
        """
        Predict average lap times.

        Args:
            features_df: DataFrame with feature columns

        Returns:
            Predicted lap times (seconds)
        """
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before prediction")

        X = features_df[self.feature_names]
        return self.model.predict(X)

    def _validate(self, X: pd.DataFrame, y: pd.Series) -> ModelValidation:
        """
        Validate model with cross-validation and sanity checks.

        Args:
            X: Features
            y: Target

        Returns:
            ModelValidation object
        """
        # R² on training data
        y_pred = self.model.predict(X)
        r2 = r2_score(y, y_pred)
        mae = mean_absolute_error(y, y_pred)

        # Cross-validation (Leave-One-Out for small datasets)
        loo = LeaveOneOut()
        cv_scores = cross_val_score(self.model, X, y, cv=loo, scoring='r2')

        # Sanity checks on coefficients
        sanity_checks = {
            'degradation_positive': self.model.coef_[0] > 0,  # More degradation → slower laps
            'consistency_positive': self.model.coef_[1] > 0,  # Less consistent → slower avg
            'traffic_positive': self.model.coef_[2] > 0,      # More traffic → slower laps
        }

        return ModelValidation(
            r2_score=r2,
            cv_r2_mean=cv_scores.mean(),
            cv_r2_std=cv_scores.std(),
            mae=mae,
            sanity_checks_passed=all(sanity_checks.values()),
            sanity_check_results=sanity_checks
        )

    def get_feature_importance(self) -> pd.DataFrame:
        """
        Get feature importance (absolute coefficient values).

        Returns:
            DataFrame sorted by importance
        """
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted first")

        importance = pd.DataFrame({
            'feature': self.feature_names,
            'coefficient': self.model.coef_,
            'abs_coefficient': np.abs(self.model.coef_)
        })

        return importance.sort_values('abs_coefficient', ascending=False)


def train_lap_time_model(
    race_data: pd.DataFrame,
    stint: str = 'full',
    verbose: bool = True
) -> LapTimeModel:
    """
    Convenience function to extract features and train model.

    Args:
        race_data: Full race data
        stint: Which stint to analyze
        verbose: Print training info

    Returns:
        Trained LapTimeModel
    """
    from .feature_extractor import extract_race_features

    if verbose:
        print(f"Extracting features for stint: {stint}")

    features = extract_race_features(race_data, stint=stint)

    if verbose:
        print(f"Training on {len(features)} drivers\n")

    model = LapTimeModel()
    model.fit(features, verbose=verbose)

    return model
