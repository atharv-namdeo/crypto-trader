import React from 'react';
import { TrendingUp, TrendingDown } from 'lucide-react';

const RiskCard = ({ title, value, subValue, trend, color = 'blue' }) => {
  const borderColors = {
    blue: 'border-l-[var(--accent-primary)]',
    green: 'border-l-[var(--accent-success)]',
    red: 'border-l-[var(--accent-danger)]',
    amber: 'border-l-[var(--accent-warning)]',
  };

  return (
    <div className={`card p-4 flex items-center justify-between border-l-4 ${borderColors[color] || borderColors.blue}`}>
      <div className="space-y-1">
        <h3 className="text-[10px] font-bold text-text-tertiary uppercase tracking-wider">{title}</h3>
        <div className="font-mono text-xl font-bold text-text-primary">{value}</div>
        <div className="text-[11px] text-text-secondary">{subValue}</div>
      </div>
      
      <div className={`p-2 rounded-full ${trend === 'up' ? 'bg-accent-success/10 text-accent-success' : 'bg-accent-danger/10 text-accent-danger'}`}>
        {trend === 'up' ? <TrendingUp size={20} /> : <TrendingDown size={20} />}
      </div>
    </div>
  );
};

export default RiskCard;
