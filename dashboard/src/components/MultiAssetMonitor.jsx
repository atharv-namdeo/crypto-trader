import React from 'react';
import { TrendingUp, TrendingDown, Zap, BarChart3, AlertTriangle } from 'lucide-react';

const MultiAssetMonitor = ({ marketData, signals }) => {
  // Extract all symbols from marketData keys
  const symbols = Object.keys(marketData).filter(s => s.includes('/USDT'));

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between px-2">
        <h3 className="text-sm font-black uppercase tracking-widest text-text-secondary flex items-center gap-2">
          <BarChart3 size={16} className="text-accent" />
          Multi-Asset Portfolio Monitor
        </h3>
        <span className="text-[10px] text-text-muted font-bold">
          {symbols.length} ASSETS ONLINE
        </span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-5 gap-4">
        {symbols.map(symbol => {
          const data = marketData[symbol] || {};
          const price = data.price || 0;
          const change = data.change || 0;
          const isUp = change >= 0;
          
          // Find latest signal for this symbol
          const mlSignal = signals.find(s => s.symbol === symbol) || { signal: 'HOLD', confidence: 0 };

          return (
            <div key={symbol} className="card p-3 border-l-4 transition-all hover:bg-bg-tertiary" 
                 style={{ borderLeftColor: isUp ? '#00ff9d' : '#ff4d4d' }}>
              <div className="flex justify-between items-start mb-2">
                <span className="text-xs font-black mono text-text-primary">{symbol.split('/')[0]}</span>
                <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                  mlSignal.signal === 'BUY' ? 'bg-green/20 text-green' :
                  mlSignal.signal === 'SELL' ? 'bg-red/20 text-red' :
                  'bg-bg-secondary text-text-muted'
                }`}>
                  {mlSignal.signal} {(mlSignal.confidence * 100).toFixed(0)}%
                </span>
              </div>
              
              <div className="flex flex-col gap-1">
                <div className="flex items-center justify-between">
                  <span className="text-lg font-black mono tracking-tight">
                    ${price < 1 ? price.toFixed(4) : price.toLocaleString()}
                  </span>
                </div>
                
                <div className="flex items-center justify-between text-[10px] font-bold uppercase">
                  <span className={isUp ? 'text-green' : 'text-red'}>
                    {isUp ? '+' : ''}{change.toFixed(2)}%
                  </span>
                  {data.vol_ratio > 1.5 && (
                    <span className="text-yellow flex items-center gap-0.5">
                      <Zap size={10} /> VOL SPIKE
                    </span>
                  )}
                </div>
              </div>

              {/* Minichart / Momentum sparkline placeholder */}
              <div className="mt-2 h-1 bg-bg-secondary rounded-full overflow-hidden opacity-30">
                <div 
                  className={`h-full ${isUp ? 'bg-green' : 'bg-red'}`} 
                  style={{ width: `${Math.min(Math.abs(change) * 10, 100)}%` }}
                ></div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default MultiAssetMonitor;
