import React from 'react';
import { Shield, Target, Zap, Waves } from 'lucide-react';

const RiskMetrics = ({ metrics }) => {
  const items = [
    { label: 'Sharpe Ratio', value: metrics.sharpe?.toFixed(2) || '0.00', icon: Shield, color: 'text-accent', sub: 'Risk-Adj Return' },
    { label: 'Profit Factor', value: metrics.profit_factor?.toFixed(2) || '0.00', icon: Target, color: 'text-blue', sub: 'Gross Profit/Loss' },
    { label: 'Win Rate', value: `${(metrics.win_rate * 100 || 0).toFixed(1)}%`, icon: Zap, color: 'text-green', sub: 'Total Accuracy' },
    { label: 'Max Drawdown', value: `${(metrics.max_drawdown || 0).toFixed(2)}%`, icon: Waves, color: 'text-red', sub: 'Peak-to-Trough' },
  ];

  return (
    <div className="card p-5 grid grid-cols-2 lg:grid-cols-4 gap-6">
      {items.map((item, idx) => (
        <div key={idx} className={`flex flex-col gap-2 ${idx > 0 && idx % 2 === 0 ? 'border-l-0 lg:border-l' : idx > 0 ? 'border-l' : ''} border-border pl-0 md:pl-6 first:pl-0`}>
          <div className="flex items-center gap-2">
            <div className={`p-1.5 rounded-md ${item.color.replace('text-', 'bg-')}-dim ${item.color}`}>
              <item.icon size={14} />
            </div>
            <span className="stat-label">{item.label}</span>
          </div>
          <div className="flex flex-col">
            <span className={`text-2xl font-black mono tracking-tight ${item.color}`}>{item.value}</span>
            <span className="text-[10px] text-text-muted font-bold uppercase tracking-widest">{item.sub}</span>
          </div>
        </div>
      ))}
    </div>
  );
};

export default RiskMetrics;
