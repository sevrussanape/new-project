import React, { useState } from 'react';
import axios from 'axios';
import SearchBar from './components/SearchBar';
import StockInfo from './components/StockInfo';
import PriceChart from './components/PriceChart';
import ModelMetrics from './components/ModelMetrics';

function App() {
  const [stockData, setStockData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const fetchStockData = async (ticker) => {
    setLoading(true);
    setError('');
    try {
      const response = await axios.get(`http://localhost:5000/api/stock/${ticker}`);
      setStockData(response.data);
    } catch (err) {
      if (err.response && err.response.status === 404) {
        try {
          const searchRes = await axios.get(`http://localhost:5000/api/search/${ticker}`);
          const results = searchRes.data;
          if (results && results.length > 0) {
            const foundTicker = results[0].symbol;
            const retryRes = await axios.get(`http://localhost:5000/api/stock/${foundTicker}`);
            setStockData(retryRes.data);
          } else {
            setError(`No stock found for "${ticker}". Please check the ticker or company name.`);
          }
        } catch (searchErr) {
          setError(`Failed to search for "${ticker}". Please check the ticker.`);
        }
      } else {
        setError('Failed to fetch stock data. Please check the ticker.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen p-4 md:p-8">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-10 fade-in">
          <h1 className="text-4xl md:text-5xl font-extrabold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
            AI Stock Price Predictor
          </h1>
          <p className="text-gray-600 mt-2">Powered by Random Forest &amp; yfinance</p>
        </div>

        <SearchBar onSearch={fetchStockData} loading={loading} />

        {loading && (
          <div className="flex justify-center mt-8">
            <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
          </div>
        )}

        {error && <div className="text-red-500 text-center mt-4">{error}</div>}

        {stockData && (
          <div className="mt-8 fade-in space-y-8">
            <StockInfo info={stockData.info} />
            <PriceChart historical={stockData.historical} predictions={stockData.predictions} />
            <ModelMetrics metrics={stockData.metrics} />
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
