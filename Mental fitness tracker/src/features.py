"""Feature engineering and preprocessing for mental fitness models."""

from dataclasses import dataclass

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src.data_generator import FEATURE_COLUMNS


@dataclass
class FeatureConfig:
    feature_columns: list[str]
    target_column: str = "mental_fitness_score"


DEFAULT_CONFIG = FeatureConfig(feature_columns=FEATURE_COLUMNS)


def build_preprocessor(config: FeatureConfig = DEFAULT_CONFIG) -> ColumnTransformer:
    """Standardize numeric lifestyle features."""
    return ColumnTransformer(
        transformers=[
            ("scale", StandardScaler(), get_model_features(config)),
        ],
        remainder="drop",
    )


def attach_engineered_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add derived features that improve prediction reliability."""
    enriched = df.copy()
    enriched["sleep_deficit"] = (7.5 - enriched["sleep_hours"]).clip(-3, 3)
    enriched["activity_index"] = (
        enriched["exercise_minutes"] + enriched["meditation_minutes"]
    ) / 90
    enriched["digital_balance"] = enriched["screen_time_hours"] - enriched["social_hours"]
    enriched["wellness_ratio"] = enriched["mood_score"] / enriched["stress_level"].clip(lower=1)
    return enriched


def get_model_features(config: FeatureConfig = DEFAULT_CONFIG) -> list[str]:
    """Return full feature set used by the trained pipeline."""
    base = list(config.feature_columns)
    engineered = ["sleep_deficit", "activity_index", "digital_balance", "wellness_ratio"]
    return base + engineered


def prepare_training_frame(df: pd.DataFrame, config: FeatureConfig = DEFAULT_CONFIG):
    """Return X, y arrays ready for sklearn."""
    enriched = attach_engineered_features(df)
    features = get_model_features(config)
    x = enriched[features]
    y = enriched[config.target_column]
    return x, y


def build_model_pipeline(estimator) -> Pipeline:
    """Wrap estimator with scaling on raw + engineered features."""
    return Pipeline(
        steps=[
            ("preprocess", build_preprocessor()),
            ("model", estimator),
        ]
    )
