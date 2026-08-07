import React from 'react';
import { Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

function PriceChart({ historical, predictions }) {
  const historicalDates = historical.map(row => row.Date.slice(0, 10));
  const lastDate = new Date(historical[historical.length - 1].Date);
  const futureDates = [];
  for (let i = 1; i <= predictions.length; i++) {
    const d = new Date(lastDate);
    d.setDate(d.getDate() + i);
    futureDates.push(d.toISOString().slice(0, 10));
  }
  const labels = [...historicalDates, ...futureDates];

  const historicalClose = historical.map(row => row.Close);
  const predictionData = Array(historicalClose.length).fill(null).concat(predictions);

  // Gradient for historical line fill
  const gradient = document.createElement('canvas').getContext('2d');
  const gradientFill = gradient.createLinearGradient(0, 0, 0, 400);
  gradientFill.addColorStop(0, 'rgba(75, 192, 192, 0.4)');
  gradientFill.addColorStop(1, 'rgba(75, 192, 192, 0.0)');

  const data = {
    labels: labels,
    datasets: [
      {
        label: 'Historical Close',
        data: historicalClose,
        borderColor: 'rgb(75, 192, 192)',
        backgroundColor: gradientFill,
        fill: true,
        tension: 0.4,
        pointRadius: 0,
        pointHoverRadius: 6,
      },
      {
        label: 'Predicted Close',
        data: predictionData,
        borderColor: 'rgb(255, 99, 132)',
        backgroundColor: 'rgba(255, 99, 132, 0.1)',
        borderDash: [8, 4],
        tension: 0.4,
        pointRadius: 4,
        pointBackgroundColor: 'rgb(255, 99, 132)',
        pointHoverRadius: 8,
      },
    ],
  };

  const options = {
    responsive: true,
    animation: {
      duration: 1200,
      easing: 'easeOutQuart',
    },
    plugins: {
      legend: {
        labels: {
          usePointStyle: true,
          boxWidth: 6,
        },
      },
      tooltip: {
        backgroundColor: 'rgba(0,0,0,0.7)',
        titleColor: '#fff',
        bodyColor: '#eee',
        borderColor: 'rgba(255,255,255,0.2)',
        borderWidth: 1,
        padding: 12,
        callbacks: {
          label: function(context) {
            let label = context.dataset.label || '';
            if (context.parsed.y !== null) {
              label += ': $' + context.parsed.y.toFixed(2);
            }
            return label;
          }
        }
      },
      title: {
        display: true,
        text: 'Stock Price (Close) – Historical & Predicted',
        color: '#1e293b',
        font: { size: 18, weight: 'bold' },
        padding: { bottom: 20 },
      },
    },
    scales: {
      x: {
        grid: { display: false },
        ticks: { maxTicksLimit: 20, color: '#64748b' },
      },
      y: {
        grid: { color: 'rgba(0,0,0,0.05)' },
        ticks: { color: '#64748b', callback: value => '$' + value.toFixed(0) },
      },
    },
    interaction: {
      intersect: false,
      mode: 'index',
    },
  };

  return (
    <div className="glass-card rounded-2xl p-6 transition-all duration-300 hover:shadow-xl">
      <Line data={data} options={options} />
    </div>
  );
}

export default PriceChart;