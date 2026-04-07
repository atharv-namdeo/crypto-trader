import React, { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Play, 
  Settings2, 
  LineChart as LineIcon, 
  List, 
  Download, 
  ChevronRight
} from 'lucide-react';
import Badge from '../ui/Badge';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

const Backtester = () => {
  const [isRunning, setIsRunning] = useState(false);
  const [showResults, setShowResults] = useState(false);
  const [results, setResults] = useState<any>(null);
  const [dates, setDates] = useState({
    start: '2022-01-01',
    end: '2022-04-01'
  });
  const [config, setConfig] = useState({
    strategy: 'AI_ENSEMBLE',
    asset: 'BTC/USDT',
    timeframe: '15m'
  });

  // Derived equity data from results
  const equityData = useMemo(() => {
    if (!results?.equity_curve) {
        return Array.from({ length: 20 }, (_, i) => ({ day: i, balance: 10000 }));
    }
    return results.equity_curve.map((p: any, i: number) => ({
        day: i,
        balance: p.balance,
        time: p.time
    }));
  }, [results]);

  const pollResults = async () => {
    try {
      const res = await fetch('/api/v1/backtest/results');
      const data = await res.json();
      if (data.status === 'idle' && data.results?.status === 'success') {
        setIsRunning(false);
        setShowResults(true);
        setResults(data.results);
        return true;
      }
    } catch (e) {
      console.error("Polling error", e);
    }
    return false;
  };

  const runBacktest = async () => {
    setIsRunning(true);
    setShowResults(false);
    setResults(null);

    try {
      await fetch('/api/v1/backtest/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          symbol: config.asset,
          start: dates.start,
          end: dates.end
        })
      });

      const interval = setInterval(async () => {
        const done = await pollResults();
        if (done) clearInterval(interval);
      }, 3000);

    } catch (e) {
      setIsRunning(false);
      console.error("Backtest trigger failed", e);
    }
  };

  return (
    <div className="flex flex-col gap-8 pb-20 animate-fade-in">
       {/* HEADER */}
      <header className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-black tracking-tight text-text-primary flex items-center gap-3">
            <Play className="text-accent-primary" />
            Professional Backtester
          </h1>
          <p className="text-sm text-text-tertiary font-medium">Verify alpha and optimize parameters against historical liquidity</p>
        </div>
        <div className="flex gap-2">
           <button className="flex items-center gap-2 px-4 py-2 bg-bg-secondary border border-border rounded-xl text-[11px] font-black uppercase tracking-widest text-text-tertiary hover:text-text-primary transition-all">
             <Download size={14} />
             Export Report
           </button>
        </div>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* LEFT: CONFIGURATION PANEL */}
        <aside className="lg:col-span-4 flex flex-col gap-6">
          <section className="bg-bg-secondary border border-border rounded-2xl p-6 shadow-sm">
            <h2 className="text-[11px] font-black text-text-primary uppercase tracking-[0.2em] mb-8 flex items-center gap-2">
              <Settings2 size={14} className="text-accent-primary" />
              Engine Configuration
            </h2>
            
            <div className="space-y-6">
              <div className="space-y-2">
                <label className="text-[10px] font-black text-text-tertiary uppercase tracking-widest">Select Strategy</label>
                <select className="w-full bg-bg-primary border border-border rounded-xl px-4 py-3 text-sm font-bold text-text-primary focus:outline-none focus:border-accent-primary transition-all appearance-none cursor-pointer">
                  <option value="AI_ENSEMBLE">AI Ensemble Layer V2</option>
                  <option value="SCALPER">HF Scalping Engine</option>
                  <option value="SWING">Trend Component Meta</option>
                </select>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-[10px] font-black text-text-tertiary uppercase tracking-widest">Asset Pair</label>
                  <select 
                    value={config.asset}
                    onChange={(e) => setConfig({...config, asset: e.target.value})}
                    className="w-full bg-bg-primary border border-border rounded-xl px-4 py-3 text-sm font-bold text-text-primary focus:outline-none focus:border-accent-primary transition-all appearance-none cursor-pointer"
                  >
                    <option>BTC/USDT</option>
                    <option>ETH/USDT</option>
                    <option>SOL/USDT</option>
                  </select>
                </div>
                <div className="space-y-2">
                  <label className="text-[10px] font-black text-text-tertiary uppercase tracking-widest">Timeframe</label>
                  <select 
                    value={config.timeframe}
                    onChange={(e) => setConfig({...config, timeframe: e.target.value})}
                    className="w-full bg-bg-primary border border-border rounded-xl px-4 py-3 text-sm font-bold text-text-primary focus:outline-none focus:border-accent-primary transition-all appearance-none cursor-pointer"
                  >
                    <option>5m</option>
                    <option>15m</option>
                    <option>1h</option>
                    <option>4h</option>
                  </select>
                </div>
              </div>

              {/* DATE RANGE SELECTION */}
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-[10px] font-black text-text-tertiary uppercase tracking-widest">Start Date</label>
                  <input 
                    type="date"
                    value={dates.start}
                    onChange={(e) => setDates({...dates, start: e.target.value})}
                    className="w-full bg-bg-primary border border-border rounded-xl px-4 py-3 text-[12px] font-mono font-bold text-text-primary focus:outline-none focus:border-accent-primary transition-all"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-[10px] font-black text-text-tertiary uppercase tracking-widest">End Date</label>
                  <input 
                    type="date"
                    value={dates.end}
                    onChange={(e) => setDates({...dates, end: e.target.value})}
                    className="w-full bg-bg-primary border border-border rounded-xl px-4 py-3 text-[12px] font-mono font-bold text-text-primary focus:outline-none focus:border-accent-primary transition-all"
                  />
                </div>
              </div>

              <div className="pt-4">
                <button 
                  onClick={runBacktest}
                  disabled={isRunning}
                  className={`w-full py-4 rounded-xl flex items-center justify-center gap-3 font-black uppercase tracking-widest transition-all
                    ${isRunning ? 'bg-bg-tertiary text-text-tertiary animate-pulse' : 'bg-accent-primary text-bg-primary shadow-[0_8px_30px_rgba(59,130,246,0.3)] hoverScale active:scale-95'}
                  `}
                >
                  {isRunning ? 'Processing Liquidity...' : (
                    <>
                      <Play size={16} fill="currentColor" />
                      Run Simulation
                    </>
                  )}
                </button>
              </div>
            </div>
          </section>

          {/* QUICK STATS (Visible after run) */}
          <AnimatePresence>
            {showResults && (
              <motion.section 
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="bg-bg-primary border border-accent-primary/20 rounded-2xl p-6 shadow-xl"
              >
                <h3 className="text-[10px] font-black text-accent-primary uppercase tracking-[0.2em] mb-6">Simulation Result</h3>
                <div className="grid grid-cols-2 gap-6">
                  <div>
                    <span className="text-[9px] font-bold text-text-tertiary uppercase block mb-1">Net Profit</span>
                    <span className={`text-lg font-mono font-bold ${results?.metrics?.pnl_usd >= 0 ? 'text-accent-success' : 'text-accent-danger'}`}>
                      {results?.metrics?.pnl_usd >= 0 ? '+' : ''}${results?.metrics?.pnl_usd.toLocaleString()}
                    </span>
                  </div>
                  <div>
                    <span className="text-[9px] font-bold text-text-tertiary uppercase block mb-1">Total ROI</span>
                    <span className={`text-lg font-mono font-bold ${results?.metrics?.pnl_pct >= 0 ? 'text-accent-success' : 'text-accent-danger'}`}>
                      {results?.metrics?.pnl_pct >= 0 ? '+' : ''}{results?.metrics?.pnl_pct}%
                    </span>
                  </div>
                  <div>
                    <span className="text-[9px] font-bold text-text-tertiary uppercase block mb-1">Win Rate</span>
                    <span className="text-lg font-mono font-bold text-text-primary">{results?.metrics?.win_rate}%</span>
                  </div>
                  <div>
                    <span className="text-[9px] font-bold text-text-tertiary uppercase block mb-1">Trades</span>
                    <span className="text-lg font-mono font-bold text-text-primary">{results?.metrics?.total_trades}</span>
                  </div>
                </div>
              </motion.section>
            )}
          </AnimatePresence>
        </aside>

        {/* RIGHT: RESULTS & ANALYTICS */}
        <main className="lg:col-span-8 flex flex-col gap-6">
          <section className="bg-bg-secondary border border-border rounded-2xl p-6 shadow-sm flex flex-col h-[640px]">
            <div className="flex items-center justify-between mb-8">
              <div className="flex items-center gap-3">
                 <h2 className="text-[11px] font-black text-text-primary uppercase tracking-[0.2em] flex items-center gap-2">
                  <LineIcon size={14} className="text-accent-primary" />
                  Equity Curve
                </h2>
              </div>
              <div className="flex gap-2">
                 <Badge variant="primary" className="text-[9px]">Simulation Output</Badge>
              </div>
            </div>

            <div className="flex-1 w-full min-h-0 bg-bg-primary/20 rounded-xl overflow-hidden relative group">
              {!showResults && !isRunning && (
                <div className="absolute inset-0 z-10 flex flex-col items-center justify-center bg-bg-secondary/50 backdrop-blur-sm">
                  <Play size={48} className="text-accent-primary opacity-20 mb-4" />
                  <p className="text-xs font-bold text-text-tertiary uppercase tracking-widest">Execute simulation to visualize alpha</p>
                </div>
              )}
              
              {isRunning && (
                <div className="absolute inset-0 z-10 flex flex-col items-center justify-center bg-bg-secondary/20 backdrop-blur-md">
                   <div className="w-12 h-12 border-4 border-accent-primary/20 border-t-accent-primary rounded-full animate-spin"></div>
                   <p className="mt-4 text-[10px] font-black text-accent-primary uppercase tracking-[0.3em] animate-pulse">Computing Alpha...</p>
                </div>
              )}

              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={equityData} margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
                  <defs>
                    <linearGradient id="colorBalance" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e1e3a" vertical={false} />
                  <XAxis dataKey="day" hide />
                  <YAxis 
                    domain={['dataMin - 100', 'dataMax + 100']} 
                    axisLine={false} 
                    tickLine={false} 
                    tick={{ fill: '#94a3b8', fontSize: 10, fontFamily: 'monospace' }}
                    tickFormatter={(val) => `$${val.toLocaleString()}`}
                  />
                  <Tooltip 
                    contentStyle={{ background: '#0f0f1a', border: '1px solid #1e1e3a', borderRadius: '8px', fontSize: 11 }}
                    itemStyle={{ color: '#3b82f6', fontWeight: 'bold' }}
                  />
                  <Area 
                    type="monotone" 
                    dataKey="balance" 
                    stroke="#3b82f6" 
                    strokeWidth={3}
                    fillOpacity={1} 
                    fill="url(#colorBalance)" 
                    isAnimationActive={true}
                    animationDuration={1500}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
            
            {/* SIMULATED TRADE LOG */}
            <div className="mt-8 flex flex-col h-48 overflow-hidden">
               <div className="flex items-center justify-between mb-3">
                  <h3 className="text-[10px] font-black text-text-tertiary uppercase tracking-widest flex items-center gap-2">
                    <List size={12} />
                    Historical Executions
                  </h3>
               </div>
                <div className="flex-1 overflow-y-auto no-scrollbar space-y-1.5 opacity-60">
                  {(results?.trades || []).map((t: any, i: number) => (
                    <div key={i} className="flex items-center justify-between p-2 rounded bg-bg-tertiary/20 text-[10px] font-mono border border-border/20">
                      <div className="flex items-center gap-3">
                         <span className="text-text-tertiary">{t.time.split('T')[0]}</span>
                         <span className={t.side === 'BUY' || t.side === 'LONG' ? 'text-accent-success' : 'text-accent-danger'}>{t.side}</span>
                         <span className="text-text-primary">{config.asset} @ {t.reason}</span>
                      </div>
                      <div className="flex items-center gap-3">
                         <span className={t.pnl >= 0 ? 'text-accent-success' : 'text-accent-danger'}>
                           {t.pnl >= 0 ? '+' : ''}${t.pnl.toLocaleString()}
                         </span>
                         <ChevronRight size={12} className="text-text-tertiary" />
                      </div>
                    </div>
                  ))}
               </div>
            </div>
          </section>
        </main>

      </div>
    </div>
  );
};

export default Backtester;
