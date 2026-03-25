import React from 'react';
import Badge from '../ui/Badge';

const StrategyCard = ({ name, status, capital, trades, winRate, pnl, avgHold, lastSignal, signalType, utilization = 0 }) => {
  const strategyColors = {
    SCALPER: 'cyan',
    SWING: 'purple',
    POSITION: 'orange',
    AI_ENSEMBLE: 'primary',
  };

  const badgeColor = strategyColors[name] || 'default';

  return (
    <div className="card p-4 flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className={`w-1 h-4 rounded-full bg-accent-${badgeColor}`}></div>
          <h3 className="font-bold text-text-primary uppercase tracking-tight text-sm">{name}</h3>
        </div>
        <Badge variant={status === 'ACTIVE' ? 'success' : 'warning'}>{status}</Badge>
      </div>

      <div className="flex items-baseline justify-between">
        <span className="text-xs text-text-secondary">Allocated Capital</span>
        <span className="font-mono font-bold text-text-primary">${capital}</span>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <div className="text-[10px] text-text-tertiary uppercase font-bold tracking-wider">Trades Today</div>
          <div className="font-mono text-sm font-bold text-text-primary">{trades}</div>
        </div>
        <div>
          <div className="text-[10px] text-text-tertiary uppercase font-bold tracking-wider">Win Rate</div>
          <div className="font-mono text-sm font-bold text-accent-success">{winRate}%</div>
        </div>
        <div>
          <div className="text-[10px] text-text-tertiary uppercase font-bold tracking-wider">Today PnL</div>
          <div className={`font-mono text-sm font-bold ${pnl >= 0 ? 'text-accent-success' : 'text-accent-danger'}`}>
            {pnl >= 0 ? '+' : ''}${pnl}
          </div>
        </div>
        <div>
          <div className="text-[10px] text-text-tertiary uppercase font-bold tracking-wider">Avg Hold</div>
          <div className="font-mono text-sm font-bold text-text-primary">{avgHold}</div>
        </div>
      </div>

      <div className="space-y-1">
        <div className="flex justify-between text-[10px] uppercase font-bold text-text-tertiary tracking-wider">
          <span>Capital Utilization</span>
          <span>{utilization}%</span>
        </div>
        <div className="w-full h-1 bg-bg-tertiary rounded-full overflow-hidden">
          <div 
            className={`h-full bg-accent-${badgeColor} rounded-full transition-all duration-500`}
            style={{ width: `${utilization}%` }}
          ></div>
        </div>
      </div>

      <div className="mt-auto pt-3 border-t border-border flex items-center justify-between">
        <div className="text-[11px] text-text-tertiary flex items-center gap-2">
          Last: <span className="text-text-secondary font-mono">{lastSignal}</span>
        </div>
        {signalType && (
          <Badge variant={signalType === 'BUY' ? 'success' : 'danger'}>{signalType}</Badge>
        )}
      </div>
    </div>
  );
};

export default StrategyCard;
