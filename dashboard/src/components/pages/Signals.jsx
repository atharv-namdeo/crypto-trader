import React from 'react';
import FuzzyRadar from '../charts/FuzzyRadar';
import SignalHeatmap from '../charts/SignalHeatmap';

const Signals = () => {
  const mockRadarData = [
    { subject: 'RSI', A: 120, B: 40, fullMark: 150 },
    { subject: 'VWAP', A: 110, B: 60, fullMark: 150 },
    { subject: 'Volume', A: 130, B: 30, fullMark: 150 },
    { subject: 'ADX', A: 90, B: 100, fullMark: 150 },
    { subject: 'Divergence', A: 70, B: 110, fullMark: 150 },
    { subject: 'Momentum', A: 140, B: 50, fullMark: 150 },
  ];

  const scores = [
    { name: 'RSI Membership', score: 0.72, val: 8 },
    { name: 'VWAP Deviation', score: 0.45, val: 5 },
    { name: 'Volume Spike', score: 0.30, val: 3 },
    { name: 'ADX Strength', score: 0.61, val: 6 },
    { name: 'Divergence', score: 0.20, val: 2 },
  ];

  return (
    <div className="flex flex-col gap-6 animate-fade-in">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Column: Radar */}
        <div className="card p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-bold text-text-primary uppercase tracking-tight">Fuzzy Radar Chart — BTC/USDT</h3>
            <span className="text-[10px] text-text-tertiary uppercase font-bold tracking-widest">30s Update</span>
          </div>
          
          <FuzzyRadar data={mockRadarData} />

          <div className="mt-8 space-y-4">
            {scores.map((s, i) => (
              <div key={i} className="space-y-1.5">
                <div className="flex justify-between text-[11px] font-bold text-text-secondary uppercase">
                  <span>{s.name}</span>
                  <span className="font-mono">{s.score.toFixed(2)}</span>
                </div>
                <div className="flex gap-1 h-3">
                  {Array.from({ length: 10 }).map((_, idx) => (
                    <div 
                      key={idx} 
                      className={`flex-1 rounded-sm ${idx < s.val ? 'bg-accent-primary' : 'bg-bg-tertiary border border-border'}`}
                    ></div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Right Column: Heatmap */}
        <div className="card p-6">
           <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-bold text-text-primary uppercase tracking-tight">Signal Activity — Last 24 Hours</h3>
            <span className="text-[10px] text-text-tertiary uppercase font-bold tracking-widest">Global Scan</span>
          </div>

          <SignalHeatmap />

          <div className="mt-8 card bg-bg-tertiary p-4 border-dashed">
              <h4 className="text-[11px] font-bold text-accent-primary uppercase mb-3">Best Trading Hours Analysis</h4>
              <p className="text-xs text-text-secondary leading-loose">
                  Aggregated signal win rates indicate that the most profitable windows for current market conditions are <span className="text-text-primary font-bold">9:00 AM</span>, <span className="text-text-primary font-bold">2:00 PM</span>, and <span className="text-text-primary font-bold">8:00 PM IST</span>. Signal volatility is highest during US/EU session overlapping.
              </p>
              
              <div className="mt-4 flex items-end justify-between h-20 gap-1">
                  {Array.from({ length: 12 }).map((_, i) => {
                      const h = 20 + Math.random() * 60;
                      return (
                          <div 
                            key={i} 
                            style={{ height: `${h}%` }} 
                            className="flex-1 bg-accent-primary/20 hover:bg-accent-primary transition-all rounded-t-sm"
                          ></div>
                      );
                  })}
              </div>
              <div className="flex justify-between mt-2 text-[9px] font-bold text-text-tertiary uppercase">
                  <span>00h</span>
                  <span>12h</span>
                  <span>23h</span>
              </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Signals;
