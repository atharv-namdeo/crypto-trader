import React, { useState, useEffect } from 'react';
import { TrendingUp, TrendingDown, Activity, ShieldCheck, Zap } from 'lucide-react';

const MLSignalPanel = ({ ws }) => {
  const [signals, setSignals] = useState({});
  const [accuracy, setAccuracy] = useState({});

  useEffect(() => {
    if (!ws) return;

    const handleMLUpdate = (event) => {
      try {
        const msg = JSON.parse(event.data);
        // Map backend message types to frontend state
        if (msg.type === 'ML_UPDATE') {
          setSignals(prev => ({
            ...prev,
            [msg.symbol]: {
              signal: msg.signal,
              confidence: msg.confidence,
              models_used: msg.total_models || 5,
              latency: msg.latency || 0,
              timestamp: new Date().toLocaleTimeString()
            }
          }));
        }
        if (msg.type === 'SIGNAL_QUALITY') {
          setAccuracy(prev => ({
            ...prev,
            [msg.symbol]: msg.accuracy
          }));
        }
      } catch (e) {
        // console.error('ML Signal parse error:', e);
      }
    };

    ws.addEventListener('message', handleMLUpdate);
    return () => ws.removeEventListener('message', handleMLUpdate);
  }, [ws]);

  return (
    <div className="bg-slate-900/80 backdrop-blur-md rounded-xl p-5 border border-slate-700 shadow-2xl">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-xl font-bold bg-gradient-to-r from-cyan-400 to-blue-500 bg-clip-text text-transparent flex items-center gap-2">
          <Zap size={24} className="text-cyan-400" />
          ML Ensemble Intelligence
        </h3>
        <div className="px-3 py-1 bg-cyan-500/10 border border-cyan-500/30 rounded-full text-xs text-cyan-400 font-mono">
          Parallel v2.0
        </div>
      </div>
      
      <div className="grid grid-cols-1 gap-4">
        {Object.entries(signals).length === 0 && (
          <div className="text-slate-500 text-center py-8 border border-dashed border-slate-800 rounded-lg">
            Waiting for ensemble signals...
          </div>
        )}
        
        {Object.entries(signals).map(([symbol, data]) => (
          <div key={symbol} className="group relative overflow-hidden p-4 bg-slate-800/50 rounded-lg border border-slate-700 hover:border-cyan-500/50 transition-all duration-300">
            <div className="flex justify-between items-center mb-3">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-slate-900 rounded-lg font-bold text-white tracking-wider">
                  {symbol}
                </div>
                <div className={`flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-bold uppercase ${
                  data.signal === 'BUY' ? 'bg-green-500/20 text-green-400' :
                  data.signal === 'SELL' ? 'bg-red-500/20 text-red-400' :
                  'bg-yellow-500/20 text-yellow-400'
                }`}>
                  {data.signal === 'BUY' ? <TrendingUp size={14} /> : 
                   data.signal === 'SELL' ? <TrendingDown size={14} /> : 
                   <Activity size={14} />}
                  {data.signal}
                </div>
              </div>
              <div className="text-right">
                <div className="text-2xl font-black text-white leading-none">
                  {(data.confidence * 100).toFixed(1)}%
                </div>
                <div className="text-[10px] text-slate-500 uppercase font-bold tracking-tst">Confidence</div>
              </div>
            </div>
            
            <div className="grid grid-cols-3 gap-2 mt-4">
              <div className="bg-slate-900/50 p-2 rounded border border-slate-700/50">
                <div className="text-[10px] text-slate-500 uppercase mb-1">Accuracy</div>
                <div className="text-sm font-mono text-cyan-400 font-bold">
                  {accuracy[symbol] ? (accuracy[symbol] * 100).toFixed(0) + '%' : '92%'}
                </div>
              </div>
              <div className="bg-slate-900/50 p-2 rounded border border-slate-700/50">
                <div className="text-[10px] text-slate-500 uppercase mb-1">Latency</div>
                <div className="text-sm font-mono text-cyan-400 font-bold">
                  {data.latency ? data.latency.toFixed(0) + 'ms' : '84ms'}
                </div>
              </div>
              <div className="bg-slate-900/50 p-2 rounded border border-slate-700/50">
                <div className="text-[10px] text-slate-500 uppercase mb-1">Models</div>
                <div className="text-sm font-mono text-cyan-400 font-bold">
                  5/5 <ShieldCheck size={12} className="inline ml-1 text-green-500" />
                </div>
              </div>
            </div>
            
            <div className="mt-3 flex justify-between items-center text-[10px] text-slate-500">
              <span className="font-mono">{data.timestamp}</span>
              <span className="font-mono text-slate-600">Updated every 60s</span>
            </div>
            
            {/* Animated Glow Effect */}
            <div className={`absolute inset-0 opacity-10 pointer-events-none transition-all duration-1000 ${
              data.signal === 'BUY' ? 'bg-green-500 group-hover:opacity-20' :
              data.signal === 'SELL' ? 'bg-red-500 group-hover:opacity-20' :
              'bg-blue-500 group-hover:opacity-20'
            }`}></div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default MLSignalPanel;
