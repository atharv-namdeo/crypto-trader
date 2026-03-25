import React from 'react';
import EquityCurve from '../charts/EquityCurve';
import DrawdownChart from '../charts/DrawdownChart';
import KPICard from '../cards/KPICard';
import { useSocket } from '../../context/SocketContext';

const Portfolio = () => {
  const { data } = useSocket();
  const portfolio = data?.portfolio || { value: 0, sharpe: 0, drawdown: 0, win_rate: 0, profit_factor: 0 };
  const equityHistory = data?.equity_history || [];

  // Mock calendar for now as it's not in the main WS stream yet
  const days = Array.from({ length: 365 }, (_, i) => ({
    date: new Date(Date.now() - (364 - i) * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    pnl: (Math.random() - 0.4) * 100
  }));

  const getHeatmapColor = (pnl) => {
    if (pnl > 50) return 'bg-[#10b981]';
    if (pnl > 0) return 'bg-[#10b981]/50';
    if (pnl > -50) return 'bg-[#ef4444]/50';
    return 'bg-[#ef4444]';
  };

  return (
    <div className="flex flex-col gap-6 animate-fade-in">
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <KPICard title="Total Return" value={portfolio.value > 0 ? ((portfolio.value - 1000) / 1000 * 100) : 0} suffix="%" color="blue" />
        <KPICard title="Win Rate" value={portfolio.win_rate * 100} suffix="%" color="amber" />
        <KPICard title="Sharpe Ratio" value={portfolio.sharpe} color="purple" />
        <KPICard title="Profit Factor" value={portfolio.profit_factor} color="green" />
      </div>

      <div className="card p-6">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-sm font-bold text-text-primary uppercase tracking-tight">Portfolio Equity Analysis</h3>
          <div className="flex gap-4">
             <span className="text-[10px] text-text-tertiary flex items-center gap-1"><div className="w-2 h-2 rounded-full bg-[#f1f5f9]"></div> TOTAL</span>
             <span className="text-[10px] text-text-tertiary flex items-center gap-1"><div className="w-2 h-2 rounded-full bg-[#06b6d4]"></div> STRATEGIES</span>
          </div>
        </div>
        <EquityCurve data={equityHistory} />
        <DrawdownChart />
        <div className="mt-4 flex justify-between items-center text-[11px] text-text-tertiary uppercase font-bold tracking-widest">
            <span>Current Balance: ${portfolio.value.toLocaleString()}</span>
            <span className="text-accent-danger">Max Drawdown: {portfolio.drawdown.toFixed(2)}%</span>
            <span className="text-accent-success">Sentiment: {portfolio.sentiment || 'NEUTRAL'}</span>
        </div>
      </div>

      <div className="card p-6">
        <h3 className="text-sm font-bold text-text-primary uppercase tracking-tight mb-6">Execution Consistency</h3>
        <div className="overflow-x-auto no-scrollbar pb-2">
            <div className="flex flex-wrap gap-1 min-w-[800px]">
                {days.map((day, i) => (
                    <div 
                        key={i} 
                        className={`w-3.5 h-3.5 rounded-[2px] cursor-pointer hover:border hover:border-text-primary transition-all ${day.pnl === 0 ? 'bg-[#1e1e3a]' : getHeatmapColor(day.pnl)}`}
                        title={`${day.date}: ${day.pnl > 0 ? '+' : ''}${day.pnl.toFixed(2)} USD`}
                    ></div>
                ))}
            </div>
        </div>
        <div className="mt-4 flex items-center gap-2 justify-end text-[10px] text-text-tertiary uppercase font-bold">
            <span>Lower</span>
            <div className="w-3 h-3 rounded-[1px] bg-[#1e1e3a]"></div>
            <div className="w-3 h-3 rounded-[1px] bg-[#10b981]/30"></div>
            <div className="w-3 h-3 rounded-[1px] bg-[#10b981]/60"></div>
            <div className="w-3 h-3 rounded-[1px] bg-[#10b981]"></div>
            <span>Higher Activity</span>
        </div>
      </div>
    </div>
  );
};

export default Portfolio;
