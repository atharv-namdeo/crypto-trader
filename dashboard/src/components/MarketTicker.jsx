import React from 'react';
import { TrendingUp, TrendingDown, Activity } from 'lucide-react';

const MarketTicker = ({ marketData, metrics }) => {
  const symbols = ['BTC/USDT', 'ETH/USDT'];
  
  return (
    <div className="space-y-4 animate-slide-up">
      {/* Live Ticker Bar */}
      <div className="flex items-center gap-6 overflow-x-auto py-2 px-4 bg-bg-secondary border-y border-border no-scrollbar whitespace-nowrap">
        {symbols.map(s => {
          const data = marketData[s] || { price: 0, change: 0 };
          const isUp = data.change >= 0;
          return (
            <div key={s} className="flex items-center gap-2 text-sm font-bold mono">
              <span className="text-text-secondary">{s}:</span>
              <span className={isUp ? 'text-green' : 'text-red'}>${data.price.toLocaleString()}</span>
              <span className={`flex items-center ${isUp ? 'text-green' : 'text-red'} text-xs`}>
                {isUp ? <TrendingUp size={12}/> : <TrendingDown size={12}/>}
                {isUp ? '+' : ''}{data.change?.toFixed(2)}%
              </span>
            </div>
          );
        })}
        <div className="ml-auto flex items-center gap-2 text-[10px] text-text-muted uppercase tracking-widest">
          <Activity size={12} className="text-accent animate-pulse-glow" />
          Live WebSocket Engine v6.5
        </div>
      </div>

      {/* Market Stat Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 px-4">
        <StatCard 
          label="BTC 24h Change" 
          value={`${marketData['BTC/USDT']?.change >= 0 ? '+' : ''}${marketData['BTC/USDT']?.change?.toFixed(2) || 0}%`}
          isPositive={marketData['BTC/USDT']?.change >= 0}
        />
        <StatCard 
          label="ETH 24h Change" 
          value={`${marketData['ETH/USDT']?.change >= 0 ? '+' : ''}${marketData['ETH/USDT']?.change?.toFixed(2) || 0}%`}
          isPositive={marketData['ETH/USDT']?.change >= 0}
        />
        <StatCard 
          label="BTC Funding Rate" 
          value={`${(marketData['BTC/USDT']?.funding * 100).toFixed(4)}%`}
          sub="Next: 04:22:15"
        />
        <StatCard 
          label="Market Sentiment" 
          value={metrics?.sentiment || 'NEUTRAL'}
          sub="Ensemble Analysis"
          color={metrics?.sentiment === 'BULL' ? 'text-green' : metrics?.sentiment === 'BEAR' ? 'text-red' : 'text-yellow'}
        />
      </div>
    </div>
  );
};

const StatCard = ({ label, value, sub, isPositive, color }) => (
  <div className="card p-4 flex flex-col justify-between group hover:border-accent-glow cursor-default transition-all duration-300">
    <span className="stat-label grow">{label}</span>
    <div className="flex items-end justify-between mt-2">
      <span className={`text-2xl font-black mono ${color || (isPositive === undefined ? 'text-text-primary' : isPositive ? 'text-green' : 'text-red')}`}>
        {value}
      </span>
      {sub && <span className="text-[10px] text-text-muted font-bold">{sub}</span>}
    </div>
  </div>
);

export default MarketTicker;
