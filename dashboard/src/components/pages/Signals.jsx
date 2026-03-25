import React from 'react';
import FuzzyRadar from '../charts/FuzzyRadar';
import SignalHeatmap from '../charts/SignalHeatmap';
import SignalCard from '../cards/SignalCard';
import { useSocket } from '../../context/SocketContext';
import { Zap, Activity, Info } from 'lucide-react';

const Signals = () => {
  const { data, connected } = useSocket();
  const signals = data?.signals || [];
  const fuzzyScores = data?.market?.['BTC/USDT']?.fuzzy || {};

  return (
    <div className="flex flex-col gap-6 animate-fade-in">
      {/* Header Info */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-text-primary tracking-tight">Signal Intelligence</h2>
          <p className="text-[11px] text-text-tertiary font-bold uppercase tracking-widest mt-1 italic">Real-time AI Ensemble Membership & Multi-Factor Voting</p>
        </div>
        <div className="flex gap-2">
           <div className="flex items-center gap-2 px-3 py-1 bg-bg-secondary rounded border border-border">
              <span className="text-[10px] font-bold text-text-tertiary uppercase">Confidence</span>
              <span className="text-[12px] font-mono font-bold text-accent-primary">{(data?.market?.['BTC/USDT']?.confidence || 0).toFixed(1)}%</span>
           </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Fuzzy Radar */}
        <div className="lg:col-span-4 min-h-[450px]">
          <FuzzyRadar fuzzyScores={fuzzyScores} />
        </div>

        {/* Right: Distribution & Intensity */}
        <div className="lg:col-span-8 flex flex-col gap-6">
          <div className="h-[300px]">
            <SignalHeatmap data={data?.signal_heatmap || []} />
          </div>
          
          <div className="card p-4 flex-1 bg-bg-secondary/50 border-dashed border-border-bright/30">
             <div className="flex items-start gap-4">
                <div className="w-10 h-10 rounded-full bg-accent-primary/10 flex items-center justify-center text-accent-primary shrink-0">
                  <Info size={20} />
                </div>
                <div>
                   <h4 className="text-xs font-bold text-text-primary uppercase mb-2">Algorithm Insights</h4>
                   <p className="text-[12px] text-text-secondary leading-relaxed">
                     The <span className="text-accent-primary font-bold">Ensemble Voting</span> mechanism combines XGBoost, Random Forest, and Gradient Boosting models. 
                     The radar chart displays membership scores across 6 key market dimensions. High overlaps indicate strong signal consensus and a Sharpe &gt; 1.8 projection.
                   </p>
                </div>
             </div>
          </div>
        </div>
      </div>

      {/* Bottom: Detailed Recent Signals */}
      <div className="card overflow-hidden">
        <div className="px-6 py-4 border-b border-border flex items-center justify-between bg-bg-tertiary/20">
          <h3 className="text-sm font-bold text-text-primary uppercase flex items-center gap-2">
            <Activity size={16} className="text-accent-primary" />
            Signal Audit Log
          </h3>
          <span className="text-[10px] text-text-tertiary font-bold uppercase tracking-widest">Live Stream (Last 50)</span>
        </div>
        
        <div className="max-h-[500px] overflow-y-auto no-scrollbar grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 p-4 bg-bg-primary/30">
          {signals.length > 0 ? signals.map((sig, i) => (
            <SignalCard 
              key={i}
              strategy={sig.strategy} 
              symbol={sig.symbol} 
              side={sig.side} 
              score={sig.score || 0} 
              confidence={sig.confidence || 0} 
              time={sig.timestamp ? new Date(sig.timestamp).toLocaleTimeString() : '--'} 
            />
          )) : (
            <div className="col-span-full py-20 text-center text-text-tertiary text-xs italic">
              Awaiting next signal event from the Multi-Strategy Engine...
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Signals;
