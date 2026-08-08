"""Streamlit dashboard for the Mental Fitness Tracker."""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import plotly.express as px
import streamlit as st

from src.data_generator import FEATURE_COLUMNS, save_dataset
from src.predict import MODEL_PATH, predict_mental_fitness
from src.train import METRICS_PATH, train_model

DATA_PATH = PROJECT_ROOT / "data" / "mental_fitness_data.csv"

st.set_page_config(
    page_title="Mental Fitness Tracker",
    page_icon="🧠",
    layout="wide",
)

st.title("AI-Powered Mental Fitness Tracker")
st.caption(
    "Predict daily mental fitness using machine learning on sleep, mood, stress, and lifestyle signals."
)


@st.cache_data
def load_metrics() -> dict | None:
    if METRICS_PATH.exists():
        return json.loads(METRICS_PATH.read_text())
    return None


@st.cache_data
def load_history() -> pd.DataFrame:
    if not DATA_PATH.exists():
        save_dataset(DATA_PATH)
    return pd.read_csv(DATA_PATH)


def render_sidebar():
    st.sidebar.header("Daily Check-in")
    return {
        "sleep_hours": st.sidebar.slider("Sleep (hours)", 3.0, 11.0, 7.0, 0.5),
        "exercise_minutes": st.sidebar.slider("Exercise (minutes)", 0, 120, 30),
        "stress_level": st.sidebar.slider("Stress level (1-10)", 1, 10, 5),
        "mood_score": st.sidebar.slider("Mood score (1-10)", 1, 10, 7),
        "social_hours": st.sidebar.slider("Social time (hours)", 0.0, 8.0, 2.0, 0.5),
        "screen_time_hours": st.sidebar.slider("Screen time (hours)", 1.0, 14.0, 5.0, 0.5),
        "meditation_minutes": st.sidebar.slider("Meditation (minutes)", 0, 60, 10),
        "water_glasses": st.sidebar.slider("Water (glasses)", 2, 12, 6),
    }


def main():
    inputs = render_sidebar()
    metrics = load_metrics()

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("Today's Prediction")
        if not MODEL_PATH.exists():
            st.warning("No trained model found. Train one from the sidebar to get predictions.")
        else:
            result = predict_mental_fitness(inputs)
            st.metric("Mental Fitness Score", f"{result['mental_fitness_score']}/100")
            st.info(f"**{result['category']}** — {result['advice']}")

            if metrics:
                st.markdown("#### Model Reliability")
                st.write(f"- R² Score: **{metrics['r2_score']}**")
                st.write(f"- Mean Absolute Error: **{metrics['mae']}**")
                st.write(f"- Cross-validation MAE: **{metrics['cv_mae_mean']} ± {metrics['cv_mae_std']}**")

    with col2:
        st.subheader("Feature Impact Snapshot")
        df = load_history()
        corr = df[FEATURE_COLUMNS + ["mental_fitness_score"]].corr()["mental_fitness_score"].drop(
            "mental_fitness_score"
        )
        fig = px.bar(
            x=corr.values,
            y=corr.index,
            orientation="h",
            labels={"x": "Correlation", "y": "Feature"},
            title="Correlation with Mental Fitness Score",
        )
        fig.update_layout(showlegend=False, height=400)
        st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.subheader("Training & Performance")

    train_col, data_col = st.columns(2)

    with train_col:
        if st.button("Train / Retrain Model", type="primary"):
            with st.spinner("Training with cross-validation and hyperparameter tuning..."):
                results = train_model()
            st.success("Model trained successfully.")
            st.json(results)
            st.cache_data.clear()

    with data_col:
        st.markdown("#### Sample Dataset Preview")
        st.dataframe(load_history().head(10), use_container_width=True)

    if metrics:
        st.markdown("#### Best Hyperparameters")
        st.code(json.dumps(metrics.get("best_params", {}), indent=2), language="json")


if __name__ == "__main__":
    main()
