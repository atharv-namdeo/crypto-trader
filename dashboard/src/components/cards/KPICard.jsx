import React from 'react';
import CountUp from 'react-countup';

const KPICard = ({ title, value, subValue, trend, trendValue, color = 'blue', prefix = '', suffix = '', decimals = 2 }) => {
  const borderColors = {
    blue: 'border-t-[var(--accent-primary)]',
    green: 'border-t-[var(--accent-success)]',
    red: 'border-t-[var(--accent-danger)]',
    amber: 'border-t-[var(--accent-warning)]',
    purple: 'border-t-[var(--accent-purple)]',
    cyan: 'border-t-[var(--accent-cyan)]',
  };

  return (
    <div className={`card p-4 flex flex-col justify-between border-t-2 ${borderColors[color] || borderColors.blue}`}>
      <div>
        <h3 className="text-[11px] font-bold text-text-secondary uppercase tracking-wider mb-2">{title}</h3>
          <span className="font-mono font-bold text-text-primary text-2xl">
            <span>{prefix}</span>
            <CountUp end={value || 0} decimals={decimals} duration={2} separator="," />
            <span>{suffix}</span>
          </span>
      </div>

      <div className="mt-3 flex items-center justify-between">
        <span className="text-xs text-text-tertiary">{subValue}</span>
        {trendValue && (
          <span className={`text-xs font-bold ${trend === 'up' ? 'text-accent-success' : 'text-accent-danger'}`}>
            {trend === 'up' ? '▲' : '▼'} {trendValue}
          </span>
        )}
      </div>
    </div>
  );
};

export default KPICard;
