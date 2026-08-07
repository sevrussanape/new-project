from flask import Flask, jsonify
from flask_cors import CORS
import pandas as pd
import requests
from stock_data import get_stock_data
from model import train_model, predict_future

app = Flask(__name__)
CORS(app)

@app.route('/api/stock/<ticker>', methods=['GET'])
def get_stock_info(ticker):
    data, info = get_stock_data(ticker)
    if data is None or len(data) < 30:
        return jsonify({'error': 'Invalid ticker or insufficient data'}), 404

    latest = data.iloc[-1]
    previous_close = data.iloc[-2]['Close'] if len(data) > 1 else latest['Close']

    stock_info = {
        'name': info.get('longName', ticker),
        'currentPrice': float(latest['Close']),
        'previousClose': float(previous_close),
        'dayHigh': float(latest['High']),
        'dayLow': float(latest['Low']),
        'volume': int(latest['Volume']),
        'ticker': ticker
    }

    historical = data.reset_index().to_dict(orient='records')
    for row in historical:
        row['Date'] = row['Date'].isoformat()

    model, metrics, last_features = train_model(data)
    predictions = predict_future(model, last_features, data, days=7)

    response = {
        'info': stock_info,
        'historical': historical,
        'predictions': predictions,
        'metrics': metrics
    }
    return jsonify(response)

@app.route('/api/search/<query>', methods=['GET'])
def search_ticker(query):
    url = f"https://query1.finance.yahoo.com/v1/finance/search?q={query}"
    try:
        response = requests.get(url)
        data = response.json()
        quotes = data.get('quotes', [])
        results = []
        for quote in quotes[:5]:
            symbol = quote.get('symbol')
            name = quote.get('longname') or quote.get('shortname') or symbol
            if symbol and '.' not in symbol:
                results.append({'symbol': symbol, 'name': name})
        return jsonify(results)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
