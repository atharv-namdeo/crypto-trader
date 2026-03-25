import React from 'react';

const SignalHeatmap = () => {
  const indicators = ['RSI', 'VWAP', 'MACD', 'Volume', 'ADX', 'PSAR', 'BB', 'EMA'];
  const hours = Array.from({ length: 24 }, (_, i) => i);
  
  // Generate mock data for the heatmap
  const getCellColor = (strength) => {
    if (strength > 0.7) return 'bg-[#10b981]'; // Strong buy
    if (strength > 0.4) return 'bg-[#6ee7b7]'; // Weak buy
    if (strength < -0.7) return 'bg-[#ef4444]'; // Strong sell
    if (strength < -0.4) return 'bg-[#fca5a5]'; // Weak sell
    return 'bg-[#1e1e3a]'; // Neutral
  };

  return (
    <div className="flex flex-col gap-4 mt-4">
      <div className="overflow-x-auto no-scrollbar">
        <div className="min-w-[600px]">
          <div className="flex mb-2">
            <div className="w-20"></div>
            <div className="flex-1 flex justify-between px-2 text-[9px] font-bold text-text-tertiary">
              {hours.map(h => <span key={h} className="w-4 text-center">{h}h</span>)}
            </div>
          </div>
          
          {indicators.map(indicator => (
            <div key={indicator} className="flex items-center mb-1">
              <div className="w-20 text-[10px] font-bold text-text-secondary uppercase">{indicator}</div>
              <div className="flex-1 flex justify-between gap-1 px-1">
                {hours.map(h => {
                  const strength = (Math.random() - 0.5) * 2;
                  return (
                    <div 
                      key={h} 
                      className={`h-4 flex-1 rounded-sm ${getCellColor(strength)}`}
                      title={`${indicator} at ${h}:00 -> ${strength.toFixed(2)}`}
                    ></div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      </div>
      
      <div className="mt-4 pt-4 border-t border-border flex items-center justify-between">
          <div className="flex items-center gap-4">
              <div className="flex items-center gap-1.5"><div className="w-3 h-3 rounded-sm bg-[#10b981]"></div><span className="text-[10px] text-text-tertiary font-bold uppercase">Strong Buy</span></div>
              <div className="flex items-center gap-1.5"><div className="w-3 h-3 rounded-sm bg-[#1e1e3a]"></div><span className="text-[10px] text-text-tertiary font-bold uppercase">Neutral</span></div>
              <div className="flex items-center gap-1.5"><div className="w-3 h-3 rounded-sm bg-[#ef4444]"></div><span className="text-[10px] text-text-tertiary font-bold uppercase">Strong Sell</span></div>
          </div>
          <div className="text-[11px] text-text-secondary italic font-medium">Updating every 30s</div>
      </div>
    </div>
  );
};

export default SignalHeatmap;
