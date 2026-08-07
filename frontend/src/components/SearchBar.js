import React, { useState } from 'react';

function SearchBar({ onSearch, loading }) {
  const [input, setInput] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (input.trim()) {
      onSearch(input.trim().toUpperCase());
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex justify-center items-center gap-4 flex-wrap">
      <input
        type="text"
        value={input}
        onChange={(e) => setInput(e.target.value)}
        placeholder="Enter stock ticker (e.g., AAPL, TSLA, RELIANCE.NS)"
        className="border-0 rounded-full px-6 py-3 w-72 focus:outline-none focus:ring-2 focus:ring-blue-400 shadow-md bg-white/80 backdrop-blur-sm"
      />
      <button
        type="submit"
        disabled={loading}
        className="bg-gradient-to-r from-blue-500 to-purple-500 hover:from-blue-600 hover:to-purple-600 text-white font-semibold py-3 px-8 rounded-full shadow-md transition-all duration-200 transform hover:scale-105 disabled:opacity-50 disabled:hover:scale-100"
      >
        {loading ? 'Searching...' : '🔍 Search'}
      </button>
    </form>
  );
}

export default SearchBar;
