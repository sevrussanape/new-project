"""Generate synthetic mental fitness training data."""

from pathlib import Path

import numpy as np
import pandas as pd

FEATURE_COLUMNS = [
    "sleep_hours",
    "exercise_minutes",
    "stress_level",
    "mood_score",
    "social_hours",
    "screen_time_hours",
    "meditation_minutes",
    "water_glasses",
]

TARGET_COLUMN = "mental_fitness_score"


def _compute_mental_fitness_score(row: pd.Series) -> float:
    """Derive a realistic mental fitness score from lifestyle inputs."""
    sleep_score = np.clip(1 - abs(row["sleep_hours"] - 7.5) / 4, 0, 1) * 18
    exercise_score = np.clip(row["exercise_minutes"] / 60, 0, 1) * 16
    stress_score = (10 - row["stress_level"]) / 9 * 18
    mood_score = row["mood_score"] / 10 * 16
    social_score = np.clip(row["social_hours"] / 4, 0, 1) * 10
    screen_penalty = np.clip(row["screen_time_hours"] - 6, 0, 6) * 1.5
    meditation_score = np.clip(row["meditation_minutes"] / 30, 0, 1) * 12
    hydration_score = np.clip(row["water_glasses"] / 8, 0, 1) * 10

    raw = (
        sleep_score
        + exercise_score
        + stress_score
        + mood_score
        + social_score
        + meditation_score
        + hydration_score
        - screen_penalty
    )
    noise = np.random.normal(0, 3)
    return float(np.clip(raw + noise, 0, 100))


def generate_dataset(n_samples: int = 2000, seed: int = 42) -> pd.DataFrame:
    """Create a labeled dataset for model training."""
    rng = np.random.default_rng(seed)

    data = {
        "sleep_hours": rng.normal(7.0, 1.5, n_samples).clip(3, 11),
        "exercise_minutes": rng.gamma(2.5, 12, n_samples).clip(0, 120),
        "stress_level": rng.integers(1, 11, n_samples),
        "mood_score": rng.integers(1, 11, n_samples),
        "social_hours": rng.gamma(2, 1.2, n_samples).clip(0, 8),
        "screen_time_hours": rng.normal(5.5, 2, n_samples).clip(1, 14),
        "meditation_minutes": rng.gamma(1.8, 8, n_samples).clip(0, 60),
        "water_glasses": rng.integers(2, 13, n_samples),
    }

    df = pd.DataFrame(data)
    df[TARGET_COLUMN] = df.apply(_compute_mental_fitness_score, axis=1)
    return df


def save_dataset(path: Path, n_samples: int = 2000) -> Path:
    """Generate and persist dataset to CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    df = generate_dataset(n_samples=n_samples)
    df.to_csv(path, index=False)
    return path


if __name__ == "__main__":
    output = Path(__file__).resolve().parents[1] / "data" / "mental_fitness_data.csv"
    save_dataset(output)
    print(f"Saved {output}")
