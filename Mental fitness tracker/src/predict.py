"""Inference utilities for mental fitness predictions."""

from pathlib import Path

import joblib
import pandas as pd

from src.features import attach_engineered_features, get_model_features

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = PROJECT_ROOT / "models" / "mental_fitness_model.joblib"


def load_model():
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Model not found at {MODEL_PATH}. Run `python -m src.train` first."
        )
    return joblib.load(MODEL_PATH)


def predict_mental_fitness(input_data: dict) -> dict:
    """Predict mental fitness score and wellness category from daily inputs."""
    model = load_model()
    frame = pd.DataFrame([input_data])
    enriched = attach_engineered_features(frame)
    features = get_model_features()
    score = float(model.predict(enriched[features])[0])
    score = max(0.0, min(100.0, score))

    if score >= 75:
        category = "Excellent"
        advice = "Strong mental fitness. Keep your current routine consistent."
    elif score >= 55:
        category = "Good"
        advice = "Solid baseline. Small improvements in sleep or mindfulness can help."
    elif score >= 35:
        category = "Moderate"
        advice = "Focus on stress reduction, movement, and reducing excessive screen time."
    else:
        category = "Needs Attention"
        advice = "Prioritize rest, social connection, and daily recovery habits."

    return {
        "mental_fitness_score": round(score, 1),
        "category": category,
        "advice": advice,
    }
