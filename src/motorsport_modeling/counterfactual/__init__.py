"""
Counterfactual Analysis Module

Provides predictive models to answer "what if" questions about race performance.
"""

from .feature_extractor import extract_driver_features, extract_race_features
from .lap_time_model import LapTimeModel, train_lap_time_model
from .interventions import (
    Intervention,
    CounterfactualScenario,
    generate_interventions,
    generate_all_interventions,
    interventions_to_dataframe
)

__all__ = [
    'extract_driver_features',
    'extract_race_features',
    'LapTimeModel',
    'train_lap_time_model',
    'Intervention',
    'CounterfactualScenario',
    'generate_interventions',
    'generate_all_interventions',
    'interventions_to_dataframe',
]
