import React, { useState, useMemo } from 'react';
import { useSocket } from '../../context/SocketContext';
import { motion } from 'framer-motion';
import { 
  BarChart3, 
  Target, 
  Clock, 
  ChevronDown,
  Percent,
  TrendingUp,
  History
} from 'lucide-react';
import Badge from '../ui/Badge';
import ExecutionTimeline from '../charts/ExecutionTimeline';
import SignalHeatmap from '../charts/SignalHeatmap';

const StrategyPerf = () => {
  const { data } = useSocket();
  const [selectedStrategy, setSelectedStrategy] = useState('AI_ENSEMBLE');
  
  // Safe formatting helpers
  const safeNumber = (val: any) => typeof val === 'number' ? val : parseFloat(String(val || 0)) || 0;
  
  const strategies = data?.strategies || {};
  const currentData = strategies[selectedStrategy.toLowerCase()] || strategies[selectedStrategy] || {
    trades_24h: 0,
    win_rate: 0,
    daily_pnl: 0,
    status: 'OFFLINE',
    active_positions: 0
  };

  const winRate = safeNumber(currentData.win_rate).toFixed(1);

  // Mock data for the heatmap (7 days x 24 hours)
  const heatmapData = useMemo(() => {
    return Array.from({ length: 7 }, (_, day) => 
      Array.from({ length: 24 }, (_, hour) => ({
        day,
        hour,
        value: Math.random() > 0.3 ? Math.random() : 0,
        count: Math.floor(Math.random() * 50)
      }))
    ).flat();
  }, [selectedStrategy]);

  // Mock data for execution timeline
  const executionSteps: any[] = [
    { type: 'SIGNAL', title: 'Neural Alpha Signal', desc: 'Sentiment spike detected on BTC/USDT 15m timeframe.', time: '14:20:05', status: 'SUCCESS', value: 'SCORE: 0.92' },
    { type: 'ORDER', title: 'Position Entry Initiated', desc: 'Market Buy order routed to Binance Liquidity Hub.', time: '14:20:07', status: 'NEUTRAL', value: 'QTY: 0.05 BTC' },
    { type: 'FILL', title: 'Market Filled', desc: 'Order executed at $64,250.10 with 0.2bps slippage.', time: '14:20:08', status: 'SUCCESS', value: 'AVG: $64,250' },
    { type: 'EXECUTION', title: 'Target Level 1 hit', desc: 'Partial take-profit hit at +1.5% extension.', time: '14:45:12', status: 'SUCCESS', value: 'PNL: +$12.50' },
    { type: 'COMPLETION', title: 'Position Closed', desc: 'Trailing stop hit after volatility spike.', time: '15:10:00', status: 'WARNING', value: 'PNL: +$8.40' },
  ];

  return (
    <div className="flex flex-col gap-8 pb-20 animate-fade-in">
      {/* HEADER & SELECTOR */}
      <header className="flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div>
          <h1 className="text-2xl font-black tracking-tight text-text-primary">Strategy Analysis</h1>
          <p className="text-sm text-text-tertiary font-medium">Deep-dive algorithmic performance and alpha breakdown</p>
        </div>
        
        <div className="relative group">
          <select 
            value={selectedStrategy}
            onChange={(e) => setSelectedStrategy(e.target.value)}
            className="appearance-none bg-bg-secondary border border-border rounded-xl px-5 py-2.5 pr-12 text-sm font-bold text-text-primary focus:outline-none focus:border-accent-primary transition-all cursor-pointer shadow-sm hover:border-border-bright"
          >
            <option value="AI_ENSEMBLE">AI Ensemble Layer</option>
            <option value="SCALPER">High-Frequency Scalper</option>
            <option value="SWING">Trend Following Swing</option>
          </select>
          <ChevronDown className="absolute right-4 top-1/2 -translate-y-1/2 text-text-tertiary pointer-events-none group-hover:text-text-primary transition-colors" size={16} />
        </div>
      </header>

      {/* PRIMARY PERFORMANCE METRICS */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {[
          { label: 'Total PnL', value: `$${safeNumber(currentData.daily_pnl || currentData.pnl).toFixed(2)}`, icon: TrendingUp, color: safeNumber(currentData.daily_pnl || currentData.pnl) >= 0 ? 'text-accent-success' : 'text-accent-danger' },
          { label: 'Win Rate', value: `${winRate}%`, icon: Percent, color: 'text-accent-primary' },
          { label: 'Trade Count', value: safeNumber(currentData.trades_24h || currentData.trades), icon: Target, color: 'text-text-primary' },
          { label: 'Avg Hold Time', value: '42m 15s', icon: Clock, color: 'text-text-primary' }
        ].map((m, i) => (
          <div key={i} className="bg-bg-secondary border border-border rounded-xl p-5 flex items-center justify-between shadow-sm group hover:border-border-bright transition-all">
            <div className="flex flex-col">
              <span className="text-[10px] font-bold text-text-tertiary uppercase tracking-widest mb-1">{m.label}</span>
              <span className={`text-xl font-mono font-bold tracking-tighter ${m.color}`}>{m.value}</span>
            </div>
            <m.icon size={20} className="text-text-tertiary opacity-30 group-hover:opacity-100 transition-opacity" />
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* LEFT: EXECUTION TIMELINE */}
        <section className="lg:col-span-12 xl:col-span-8 bg-bg-secondary border border-border rounded-2xl p-6 flex flex-col h-[700px] shadow-sm">
          <div className="flex items-center justify-between mb-8">
            <div className="flex items-center gap-3">
              <h2 className="text-[11px] font-black text-text-primary uppercase tracking-[0.2em] flex items-center gap-2">
                <History size={14} className="text-accent-primary" />
                Live Execution Engine
              </h2>
              <div className="h-4 w-px bg-border mx-1"></div>
              <span className="text-[10px] items-center gap-1.5 hidden sm:flex text-text-tertiary font-bold tracking-widest uppercase">
                Status: <span className="text-accent-success">Operational</span>
              </span>
            </div>
            <Badge variant="primary" className="text-[9px] px-2 py-0.5">Real-time Stream</Badge>
          </div>

          <div className="flex-1 overflow-y-auto no-scrollbar pr-4">
            <ExecutionTimeline steps={executionSteps} />
          </div>
        </section>

        {/* RIGHT: ANALYSIS WIDGETS */}
        <div className="lg:col-span-12 xl:col-span-4 flex flex-col gap-6">
          <section className="bg-bg-secondary border border-border rounded-2xl p-6 shadow-sm overflow-hidden flex flex-col h-[400px]">
             <h2 className="text-[11px] font-black text-text-primary uppercase tracking-[0.2em] mb-8 flex items-center gap-2">
              <BarChart3 size={14} className="text-accent-primary" />
              Alpha Distribution
            </h2>
            <div className="flex-1 min-h-0 flex items-center justify-center">
              <SignalHeatmap data={heatmapData} />
            </div>
            <div className="mt-6 text-center">
              <p className="text-[9px] font-bold text-text-tertiary uppercase tracking-widest leading-relaxed opacity-60">
                PROFIT FACTOR DISTRIBUTION BY DAY/HOUR
              </p>
            </div>
          </section>

          <section className="bg-bg-secondary border border-border rounded-2xl p-6 shadow-sm flex flex-col h-[276px]">
            <h2 className="text-[11px] font-black text-text-primary uppercase tracking-[0.2em] mb-6">Neural Activation Score</h2>
            <div className="flex flex-col gap-5">
              {[
                { label: 'Long-Term Alpha Bias', value: 88, color: 'bg-accent-primary' },
                { label: 'Volatility Compression', value: 42, color: 'bg-accent-warning' },
                { label: 'Sentiment Momentum', value: 65, color: 'bg-accent-success' }
              ].map((f, i) => (
                <div key={i} className="space-y-2">
                  <div className="flex justify-between text-[10px] font-bold uppercase tracking-widest">
                    <span className="text-text-secondary opacity-70">{f.label}</span>
                    <span className="text-text-primary text-[11px] font-black">{f.value}%</span>
                  </div>
                  <div className="h-1.5 bg-bg-tertiary rounded-full overflow-hidden">
                    <motion.div 
                      initial={{ width: 0 }}
                      animate={{ width: `${f.value}%` }}
                      transition={{ duration: 1.5, delay: i * 0.2 }}
                      className={`h-full ${f.color}`}
                    />
                  </div>
                </div>
              ))}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
};

export default StrategyPerf;
