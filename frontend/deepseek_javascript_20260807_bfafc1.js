import React from 'react';

function StockInfo({ info }) {
  const { name, currentPrice, previousClose, dayHigh, dayLow, volume, ticker } = info;
  const items = [
    { label: 'Company', value: `${name} (${ticker})` },
    { label: 'Current Price', value: `$${currentPrice.toFixed(2)}` },
    { label: 'Previous Close', value: `$${previousClose.toFixed(2)}` },
    { label: 'Day High', value: `$${dayHigh.toFixed(2)}` },
    { label: 'Day Low', value: `$${dayLow.toFixed(2)}` },
    { label: 'Volume', value: volume.toLocaleString() },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
      {items.map((item, idx) => (
        <div
          key={idx}
          className="glass-card rounded-2xl p-4 text-center transition-all duration-200 hover:shadow-xl hover:scale-105"
        >
          <h3 className="text-xs uppercase tracking-wider text-gray-500">{item.label}</h3>
          <p className="text-lg font-bold text-gray-800 mt-1">{item.value}</p>
        </div>
      ))}
    </div>
  );
}

export default StockInfo;