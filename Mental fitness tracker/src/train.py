"""Train and evaluate mental fitness prediction models."""

import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GridSearchCV, cross_val_score, train_test_split

from src.data_generator import FEATURE_COLUMNS, TARGET_COLUMN, save_dataset
from src.features import DEFAULT_CONFIG, build_model_pipeline, prepare_training_frame

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = PROJECT_ROOT / "data" / "mental_fitness_data.csv"
MODEL_PATH = PROJECT_ROOT / "models" / "mental_fitness_model.joblib"
METRICS_PATH = PROJECT_ROOT / "models" / "metrics.json"


def load_or_create_data() -> pd.DataFrame:
    if not DATA_PATH.exists():
        save_dataset(DATA_PATH)
    return pd.read_csv(DATA_PATH)


def train_model() -> dict:
    """Train optimized Random Forest and persist best model."""
    df = load_or_create_data()
    x, y = prepare_training_frame(df, DEFAULT_CONFIG)

    x_train, x_test, y_train, y_test = train_test_split(
        x, y, test_size=0.2, random_state=42
    )

    base_estimator = RandomForestRegressor(random_state=42, n_jobs=-1)
    pipeline = build_model_pipeline(base_estimator)

    param_grid = {
        "model__n_estimators": [120, 200],
        "model__max_depth": [None, 12, 18],
        "model__min_samples_leaf": [1, 2],
    }

    search = GridSearchCV(
        pipeline,
        param_grid=param_grid,
        scoring="neg_mean_absolute_error",
        cv=5,
        n_jobs=-1,
    )
    search.fit(x_train, y_train)
    best_model = search.best_estimator_

    y_pred = best_model.predict(x_test)
    cv_scores = cross_val_score(
        best_model, x, y, cv=5, scoring="neg_mean_absolute_error", n_jobs=-1
    )

    metrics = {
        "best_params": search.best_params_,
        "r2_score": round(r2_score(y_test, y_pred), 4),
        "mae": round(mean_absolute_error(y_test, y_pred), 4),
        "rmse": round(mean_squared_error(y_test, y_pred) ** 0.5, 4),
        "cv_mae_mean": round(-cv_scores.mean(), 4),
        "cv_mae_std": round(cv_scores.std(), 4),
        "feature_columns": FEATURE_COLUMNS,
        "target_column": TARGET_COLUMN,
    }

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(best_model, MODEL_PATH)
    METRICS_PATH.write_text(json.dumps(metrics, indent=2))

    # Benchmark gradient boosting for comparison
    gb_pipeline = build_model_pipeline(
        GradientBoostingRegressor(random_state=42, n_estimators=150, max_depth=4)
    )
    gb_pipeline.fit(x_train, y_train)
    gb_mae = mean_absolute_error(y_test, gb_pipeline.predict(x_test))
    metrics["gradient_boosting_mae"] = round(gb_mae, 4)

    METRICS_PATH.write_text(json.dumps(metrics, indent=2))
    return metrics


if __name__ == "__main__":
    results = train_model()
    print("Training complete.")
    for key, value in results.items():
        print(f"  {key}: {value}")
