import React from 'react';
import Badge from '../ui/Badge';

const SignalCard = ({ strategy, symbol, side, score, confidence, time }) => {
  const strategyVariants = {
    SCALPER: 'cyan',
    SWING: 'purple',
    POSITION: 'orange',
    AI_ENSEMBLE: 'primary',
  };

  const sideVariants = {
    BUY: 'success',
    SELL: 'danger',
    HOLD: 'default',
  };

  return (
    <div className="signal-card p-3 rounded-card bg-bg-tertiary border border-border hover:border-border-bright transition-all duration-200 mb-2">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Badge variant={strategyVariants[strategy] || 'default'}>{strategy}</Badge>
          <span className="font-mono font-bold text-text-primary text-sm">{symbol}</span>
        </div>
        <Badge variant={sideVariants[side] || 'default'}>{side}</Badge>
      </div>

      <div className="flex items-center justify-between text-[11px] mb-1">
        <div className="flex gap-3">
          <span className="text-text-tertiary uppercase font-bold tracking-tighter">Score: <span className="text-text-secondary font-mono">{score.toFixed(2)}</span></span>
          <span className="text-text-tertiary uppercase font-bold tracking-tighter">Conv: <span className="text-text-secondary font-mono">{confidence.toFixed(2)}</span></span>
        </div>
        <span className="text-text-tertiary font-mono">{time}</span>
      </div>
    </div>
  );
};

export default SignalCard;
