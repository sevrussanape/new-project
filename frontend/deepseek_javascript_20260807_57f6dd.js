import React from 'react';

function ModelMetrics({ metrics }) {
  const { mae, rmse, r2 } = metrics;
  const items = [
    { label: 'MAE', value: mae.toFixed(4), color: 'from-blue-400 to-blue-600' },
    { label: 'RMSE', value: rmse.toFixed(4), color: 'from-green-400 to-green-600' },
    { label: 'R² Score', value: r2.toFixed(4), color: 'from-purple-400 to-purple-600' },
  ];

  return (
    <div className="glass-card rounded-2xl p-6">
      <h2 className="text-xl font-bold text-gray-700 mb-4">Model Evaluation Metrics</h2>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {items.map((item, idx) => (
          <div
            key={idx}
            className={`bg-gradient-to-br ${item.color} rounded-xl p-4 text-white shadow-lg transition-transform duration-200 hover:scale-105`}
          >
            <p className="text-sm uppercase tracking-wider opacity-80">{item.label}</p>
            <p className="text-2xl font-bold">{item.value}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

export default ModelMetrics;