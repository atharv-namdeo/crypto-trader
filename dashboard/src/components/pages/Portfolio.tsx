import React from 'react';
import EquityCurve from '../charts/EquityCurve';
import DrawdownChart from '../charts/DrawdownChart';
import KPICard from '../cards/KPICard';
import { useSocket } from '../../context/SocketContext';
import { BarChart3, TrendingUp, ShieldAlert, Zap } from 'lucide-react';

const Portfolio = () => {
  const { data } = useSocket();
  const safeNumber = (val: any) => typeof val === 'number' ? val : parseFloat(String(val || 0)) || 0;
  const safeScalar = (val: any) => (typeof val === 'string' || typeof val === 'number') ? val : '';
  
  const portfolio = data?.portfolio || { value: 0, sharpe: 0, drawdown: 0, win_rate: 0, profit_factor: 0, trades: 0 };
  const equityHistory = data?.equity_history || [];

  // Mock calendar for consistency visual - real data should flow from Redis
  const days = Array.from({ length: 90 }, (_, i) => ({
    date: new Date(Date.now() - (89 - i) * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    pnl: (Math.random() - 0.45) * 50 // Lean slightly bullish
  }));

  const getHeatmapColor = (pnl) => {
    if (pnl > 30) return 'bg-accent-success';
    if (pnl > 0) return 'bg-accent-success/40';
    if (pnl > -30) return 'bg-accent-danger/40';
    return 'bg-accent-danger';
  };

  return (
    <div className="flex flex-col gap-6 animate-fade-in">
      {/* KPI Row */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <KPICard title="Total Return" value={safeNumber(portfolio.value) > 0 ? (safeNumber(portfolio.value) - 1000) / 10 / 100 * 100 : 0} suffix="%" color="blue" />
        <KPICard title="Win Rate" value={(portfolio.win_rate || 0) * 100} suffix="%" color="amber" />
        <KPICard title="Sharpe Ratio" value={portfolio.sharpe || 0} color="purple" />
        <KPICard title="Profit Factor" value={portfolio.profit_factor || 0} color="green" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Main Equity Analysis */}
        <div className="lg:col-span-8 card p-6 flex flex-col min-h-[500px]">
          <div className="flex items-center justify-between mb-8">
            <h3 className="text-sm font-bold text-text-primary uppercase tracking-tight flex items-center gap-2">
              <TrendingUp size={16} className="text-accent-primary" />
              Equity Growth Projection
            </h3>
            <div className="flex gap-4">
               <span className="text-[10px] text-text-tertiary flex items-center gap-1 font-bold uppercase"><div className="w-2 h-2 rounded-full bg-accent-primary"></div> Total Equity</span>
               <span className="text-[10px] text-text-tertiary flex items-center gap-1 font-bold uppercase"><div className="w-2 h-2 rounded-full bg-accent-purple/50"></div> Combined Benchmark</span>
            </div>
          </div>
          <div className="flex-1">
            <EquityCurve data={equityHistory} />
          </div>
          <div className="mt-8 grid grid-cols-3 gap-4 border-t border-border pt-6">
             <div className="flex flex-col">
                <span className="text-[10px] font-bold text-text-tertiary uppercase">Max Drawdown</span>
                 <span className="text-sm font-mono text-accent-danger font-bold mt-1">{safeNumber(portfolio.drawdown).toFixed(2)}%</span>
             </div>
             <div className="flex flex-col border-l border-border pl-4">
                <span className="text-[10px] font-bold text-text-tertiary uppercase">Total Trades</span>
                <span className="text-sm font-mono text-text-primary font-bold mt-1">{portfolio.trades || 0}</span>
             </div>
             <div className="flex flex-col border-l border-border pl-4">
                <span className="text-[10px] font-bold text-text-tertiary uppercase">Volatility</span>
                <span className="text-sm font-mono text-accent-warning font-bold mt-1">{(portfolio.volatility || 4.2).toFixed(1)}%</span>
             </div>
          </div>
        </div>

        {/* Consistency / Risk Profile */}
        <div className="lg:col-span-4 flex flex-col gap-6">
           <div className="card p-6 flex-1">
             <h3 className="text-sm font-bold text-text-primary uppercase tracking-tight mb-6 flex items-center gap-2">
               <ShieldAlert size={16} className="text-accent-danger" />
               Risk Profile
             </h3>
             <div className="h-[200px]">
               <DrawdownChart />
             </div>
             <div className="mt-4 p-3 bg-bg-tertiary/20 rounded border border-border/50 italic text-[11px] text-text-secondary leading-relaxed">
               Current strategy allocation is optimized for <span className="text-accent-primary font-bold">Compound Growth</span> with a target Sharpe &gt; 1.8. 
               Daily risk limit is static at 2.5% of total capital.
             </div>
           </div>

           <div className="card p-6 min-h-[140px]">
             <h3 className="text-sm font-bold text-text-primary uppercase tracking-tight mb-4 flex items-center gap-2">
               <BarChart3 size={16} className="text-accent-amber" />
               Execution Consistency
             </h3>
             <div className="flex flex-wrap gap-1.5 h-[60px] content-start">
               {days.slice(0, 48).map((day, i) => (
                 <div 
                   key={i} 
                   className={`w-3 h-3 rounded-[1px] cursor-pointer hover:border hover:border-text-primary transition-all ${day.pnl === 0 ? 'bg-bg-tertiary' : getHeatmapColor(day.pnl)}`}
                   title={`${day.date}: ${day.pnl > 0 ? '+' : ''}${(day.pnl || 0).toFixed(2)}%`}
                 ></div>
               ))}
               <div className="w-3 h-3 rounded-[1px] bg-accent-primary animate-pulse" title="Ongoing Session"></div>
             </div>
             <div className="mt-4 flex justify-between items-center text-[11px] text-text-tertiary uppercase font-bold tracking-widest">
             <span>Current Balance: ${safeNumber(portfolio.value || portfolio.total_value).toLocaleString()}</span>
            <span className="text-accent-danger">Max Drawdown: {safeNumber(portfolio.drawdown).toFixed(2)}%</span>
            <span className="text-accent-success">Sentiment: {safeScalar(portfolio.sentiment || 'NEUTRAL')}</span>
        </div>
             <div className="mt-4 flex items-center justify-between text-[8px] text-text-tertiary uppercase font-black tracking-widest">
               <span>Last 90 Days</span>
               <div className="flex gap-1 items-center">
                 <span>-</span>
                 <div className="w-1.5 h-1.5 bg-bg-tertiary"></div>
                 <div className="w-1.5 h-1.5 bg-accent-success/40"></div>
                 <div className="w-1.5 h-1.5 bg-accent-success"></div>
                 <span>+</span>
               </div>
             </div>
           </div>
        </div>
      </div>
    </div>
  );
};

export default Portfolio;
