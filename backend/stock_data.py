import yfinance as yf
import pandas as pd

def get_stock_data(ticker, period='1y'):
    stock = yf.Ticker(ticker)
    info = stock.info
    hist = stock.history(period=period)
    if hist.empty:
        return None, None
    hist = hist[['Open', 'High', 'Low', 'Close', 'Volume']]
    hist = hist.dropna()
    return hist, info
