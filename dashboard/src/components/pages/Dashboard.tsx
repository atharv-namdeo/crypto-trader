import React from 'react';
import MetricSparkline from '../charts/MetricSparkline';
import CandlestickChart from '../charts/CandlestickChart';
import SignalCard from '../cards/SignalCard';
import StrategyCard from '../cards/StrategyCard';
import { useSocket } from '../../context/SocketContext';
import { motion } from 'framer-motion';
import { Activity, Brain, Zap, TrendingUp } from 'lucide-react';

const Dashboard = () => {
  const { data, connected } = useSocket();

  // Safe formatting helpers
  const safeNumber = (val: any) => typeof val === 'number' ? val : parseFloat(String(val || 0)) || 0;
  const safeScalar = (val: any) => (typeof val === 'string' || typeof val === 'number') ? val : JSON.stringify(val);
  const formatSignalTime = (ts: any) => {
    try {
      if (!ts) return '--:--';
      const d = new Date(ts);
      if (isNaN(d.getTime())) return '--:--';
      return d.toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit' });
    } catch {
      return '--:--';
    }
  };

  // Data mapping with robust fallbacks
  const portfolio = data?.portfolio || { total_value: 0, daily_pnl: 0, daily_change_pct: 0, sharpe: 0, drawdown: 0, win_rate: 0 };
  const market = data?.market || {};
  const strategies = data?.strategies || {};
  const signals = data?.signals || [];
  const latestCandles = data?.latest_candles || [];

  // Mock trend data for sparklines until backend history is ready
  const mockTrend = Array.from({ length: 20 }, (_, i) => ({ value: 50000 + Math.random() * 5000 }));

  return (
    <div className="flex flex-col gap-8 animate-fade-in pb-12">
      {/* HEADER SECTION */}
      <header className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-black tracking-tight text-text-primary flex items-center gap-3">
            Alpha Command <span className="text-accent-primary opacity-50">/</span> Overview
          </h1>
          <p className="text-sm text-text-tertiary font-medium mt-1">Multi-strategy algorithmic execution engine</p>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex flex-col items-end">
            <span className="text-[10px] font-bold text-text-tertiary uppercase tracking-widest">Global Sentiment</span>
            <div className="flex items-center gap-2">
              <div className="h-1.5 w-24 bg-bg-tertiary rounded-full overflow-hidden">
                <div className="h-full bg-accent-success w-[72%]"></div>
              </div>
              <span className="text-xs font-bold text-accent-success">BULLISH</span>
            </div>
          </div>
        </div>
      </header>

      {/* KPI STRIP - METRIC SPARKLINES */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricSparkline 
          title="Bitcoin / USDT" 
          value={safeScalar(market['BTC/USDT']?.price || '0.00')} 
          change={safeNumber(market['BTC/USDT']?.change || 0)} 
          data={mockTrend} 
          color="#f59e0b"
        />
        <MetricSparkline 
          title="Ethereum / USDT" 
          value={safeScalar(market['ETH/USDT']?.price || '0.00')} 
          change={safeNumber(market['ETH/USDT']?.change || 0)} 
          data={mockTrend} 
          color="#6366f1"
        />
        <MetricSparkline 
          title="Solana / USDT" 
          value={safeScalar(market['SOL/USDT']?.price || '0.00')} 
          change={safeNumber(market['SOL/USDT']?.change || 0)} 
          data={mockTrend} 
          color="#14f195"
        />
        <MetricSparkline 
          title="Total Equity (USD)" 
          value={safeNumber(portfolio.total_value || 0)} 
          change={safeNumber(portfolio.daily_change_pct || 2.4)} 
          data={mockTrend} 
          color="#10b981"
          prefix="$"
        />
      </div>

      {/* MAIN 3-COLUMN GRID */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* LEFT COLUMN: LIVE INTELLIGENCE FEED */}
        <aside className="lg:col-span-3 flex flex-col gap-6">
          <section className="bg-bg-secondary border border-border rounded-2xl p-5 flex flex-col h-[640px]">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-[11px] font-black text-text-primary uppercase tracking-[0.2em] flex items-center gap-2">
                <Activity size={14} className="text-accent-primary" />
                Signal Intelligence
              </h2>
              <div className="flex items-center gap-1">
                <span className={`w-1.5 h-1.5 rounded-full ${connected ? 'bg-accent-success animate-pulse' : 'bg-accent-danger'}`}></span>
                <span className="text-[9px] font-bold text-text-tertiary uppercase tracking-tighter">Live Updates</span>
              </div>
            </div>

            <div className="flex-1 overflow-y-auto no-scrollbar space-y-3">
              {signals.length > 0 ? signals.map((sig: any, i: number) => (
                <SignalCard 
                  key={i}
                  strategy={String(sig.strategy || 'UNKNOWN')} 
                  symbol={String(sig.symbol || 'N/A')} 
                  side={sig.side} 
                  score={safeNumber(sig.score || 0)} 
                  confidence={safeNumber(sig.confidence || 0)} 
                  time={formatSignalTime(sig.timestamp)} 
                />
              )) : (
                <div className="h-full flex flex-col items-center justify-center opacity-40 text-center px-4">
                  <Brain size={32} className="mb-4 text-accent-primary" />
                  <p className="text-xs font-bold leading-relaxed">Neural Engine Scanning market structures...</p>
                </div>
              )}
            </div>
          </section>
        </aside>

        {/* CENTER COLUMN: MASTER EXECUTION CHART */}
        <main className="lg:col-span-6 flex flex-col gap-6">
          <section className="bg-bg-secondary border border-border rounded-2xl p-5 flex flex-col h-[640px]">
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-4">
                <h2 className="text-[11px] font-black text-text-primary uppercase tracking-[0.2em] flex items-center gap-2">
                  <TrendingUp size={14} className="text-accent-primary" />
                  Execution Flow
                </h2>
                <div className="h-4 w-px bg-border mx-1"></div>
                <div className="flex items-center gap-2">
                  <span className="text-[13px] font-mono font-bold text-text-primary">BTC/USDT</span>
                  <span className="text-[11px] font-mono font-bold text-accent-success">+1.24%</span>
                </div>
              </div>
              <div className="flex gap-1.5">
                {['1m', '5m', '15m', '1h', '4h'].map(tf => (
                  <button key={tf} className={`px-2 py-0.5 rounded text-[10px] font-bold transition-all border ${tf === '15m' ? 'bg-accent-primary text-bg-primary border-accent-primary' : 'bg-bg-tertiary text-text-tertiary border-border hover:border-border-bright'}`}>
                    {tf.toUpperCase()}
                  </button>
                ))}
              </div>
            </div>
            
            <div className="flex-1 min-h-0 bg-bg-primary/30 rounded-xl border border-border/50 overflow-hidden relative group">
              <CandlestickChart data={latestCandles} symbol="BTC/USDT" />
              {/* Overlay for price watermark */}
              <div className="absolute top-4 right-4 text-4xl font-black text-text-primary opacity-5 select-none pointer-events-none tracking-tighter uppercase italic">
                Quant Engine V8
              </div>
            </div>
          </section>
        </main>

        {/* RIGHT COLUMN: STRATEGY PERFORMANCE HUB */}
        <aside className="lg:col-span-3 flex flex-col gap-6">
          <section className="bg-bg-secondary border border-border rounded-2xl p-5 flex flex-col h-[640px]">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-[11px] font-black text-text-primary uppercase tracking-[0.2em] flex items-center gap-2">
                <Zap size={14} className="text-accent-primary" />
                Alpha Strategies
              </h2>
              <span className="text-[9px] font-bold text-text-tertiary uppercase tracking-widest">Performance</span>
            </div>

            <div className="flex-1 overflow-y-auto no-scrollbar space-y-4">
              {['SCALPER', 'SWING', 'AI_ENSEMBLE'].map(s => {
                const sData = strategies[s.toLowerCase()] || strategies[s] || { 
                  trades_24h: 0, 
                  win_rate: 0, 
                  daily_pnl: 0, 
                  status: 'SCANNING', 
                  active_positions: 0 
                };
                
                return (
                  <StrategyCard 
                    key={s}
                    name={s} 
                    status={sData.status || 'SCANNING'} 
                    capital={s === 'AI_ENSEMBLE' ? 500 : 250} 
                    trades={sData.trades_24h} 
                    winRate={String(sData.win_rate || '0.0')} 
                    pnl={sData.daily_pnl || 0} 
                    avgHold={s === 'SCALPER' ? '4m 12s' : s === 'SWING' ? '2h 45m' : 'Auto'} 
                    utilization={sData.active_positions > 0 ? 80 : 0} 
                    lastSignal={sData.last_trade || 'N/A'}
                  />
                );
              })}
            </div>
          </section>
        </aside>

      </div>
    </div>
  );
};

export default Dashboard;
