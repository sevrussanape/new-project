# Mental Fitness Tracker

An AI-powered application that predicts daily mental fitness from lifestyle signals using machine learning. Built to improve prediction accuracy and reliability through cross-validated model tuning and engineered wellness features.

## Features

- **ML prediction engine** — Random Forest regressor with GridSearchCV hyperparameter optimization
- **Reliability metrics** — R², MAE, RMSE, and 5-fold cross-validation scores
- **Feature engineering** — Sleep deficit, activity index, digital balance, and wellness ratio
- **Interactive dashboard** — Streamlit UI for daily check-ins and model insights
- **Synthetic data pipeline** — Reproducible dataset generation for training and demos

## Project Structure

```
mental-fitness-tracker/
├── app/
│   └── streamlit_app.py      # Dashboard UI
├── data/                     # Generated training data
├── models/                   # Saved model + metrics
├── src/
│   ├── data_generator.py     # Synthetic dataset creation
│   ├── features.py           # Feature engineering & preprocessing
│   ├── train.py              # Model training & evaluation
│   └── predict.py            # Inference API
└── requirements.txt
```

## Quick Start

```bash
# 1. Create virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Train the model
python -m src.train

# 4. Launch the dashboard
streamlit run app/streamlit_app.py
```

## Input Features

| Feature | Description |
|---------|-------------|
| Sleep hours | Hours of sleep last night |
| Exercise minutes | Physical activity duration |
| Stress level | Self-reported stress (1–10) |
| Mood score | Self-reported mood (1–10) |
| Social hours | Time spent with others |
| Screen time | Daily device usage (hours) |
| Meditation | Mindfulness practice (minutes) |
| Water intake | Glasses of water consumed |

## Model Performance

After training, metrics are saved to `models/metrics.json`:

- **R² Score** — Explained variance in mental fitness
- **MAE** — Average prediction error (points on 0–100 scale)
- **CV MAE** — Cross-validation mean absolute error for reliability

## Tech Stack

- Python 3.10+
- scikit-learn (Random Forest, Gradient Boosting, GridSearchCV)
- Streamlit
- Plotly
- pandas / numpy

## Author

Deepanshukashyap8835 — Data Scientist
