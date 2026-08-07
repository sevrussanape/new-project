import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import joblib
import os

def train_model(data):
    X = data[['Open', 'High', 'Low', 'Volume']].values[:-1]
    y = data['Close'].values[1:]
    split_idx = int(len(X) * 0.8)
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]

    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    r2 = r2_score(y_test, y_pred)
    last_features = X[-1]
    return model, {'mae': mae, 'rmse': rmse, 'r2': r2}, last_features

def predict_future(model, last_features, data, days=7):
    data['High_ratio'] = data['High'] / data['Open']
    data['Low_ratio'] = data['Low'] / data['Open']
    avg_high_ratio = data['High_ratio'].mean()
    avg_low_ratio = data['Low_ratio'].mean()
    avg_volume = data['Volume'].mean()

    features = last_features.copy()
    predictions = []
    for _ in range(days):
        next_close = model.predict([features])[0]
        predictions.append(next_close)
        next_open = next_close
        next_high = next_open * avg_high_ratio
        next_low = next_open * avg_low_ratio
        next_volume = avg_volume
        features = np.array([next_open, next_high, next_low, next_volume])
    return predictions

def save_model(model, ticker):
    os.makedirs('models', exist_ok=True)
    joblib.dump(model, f'models/{ticker}_model.pkl')
