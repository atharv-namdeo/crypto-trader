import React from 'react';
import Badge from '../ui/Badge';
import { motion } from 'framer-motion';

interface StrategyCardProps {
  name: string;
  status: string;
  capital: number;
  trades: number;
  winRate: number | string;
  pnl: number | string;
  avgHold: string;
  lastSignal?: string;
  signalType?: 'BUY' | 'SELL' | 'HOLD';
  utilization?: number;
}

const StrategyCard: React.FC<StrategyCardProps> = ({ 
  name, 
  status, 
  capital, 
  trades, 
  winRate, 
  pnl, 
  avgHold, 
  lastSignal, 
  signalType, 
  utilization = 0 
}) => {
  const safeNumber = (val: any) => typeof val === 'number' ? val : parseFloat(String(val || 0)) || 0;
  const safeScalar = (val: any) => (typeof val === 'string' || typeof val === 'number') ? val : '';
  const strategyColors: Record<string, string> = {
    SCALPER: 'cyan',
    SWING: 'purple',
    POSITION: 'orange',
    AI_ENSEMBLE: 'primary',
  };

  const badgeVariant = strategyColors[name.toUpperCase()] || 'default';
  const numericPnl = safeNumber(pnl);

  return (
    <motion.div 
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-bg-secondary border border-border rounded-xl p-4 flex flex-col gap-4 hover:border-border-bright transition-all shadow-sm group"
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className={`w-1 h-5 rounded-full bg-accent-${badgeVariant}`}></div>
          <h3 className="font-bold text-text-primary uppercase tracking-tight text-[13px]">{safeScalar(name)}</h3>
        </div>
        <Badge variant={status === 'ACTIVE' ? 'success' : 'warning'} className="text-[9px] px-1.5 py-0.5">{safeScalar(status)}</Badge>
      </div>

      <div className="flex items-baseline justify-between py-1 border-y border-border/30">
        <span className="text-[11px] font-bold text-text-tertiary uppercase tracking-wider opacity-70">Capital</span>
        <span className="font-mono font-bold text-text-primary text-sm">${safeNumber(capital).toLocaleString()}</span>
      </div>

      <div className="grid grid-cols-2 gap-y-4 gap-x-6">
        <div>
          <div className="text-[9px] text-text-tertiary uppercase font-bold tracking-wider opacity-60 mb-0.5">Trades</div>
          <div className="font-mono text-xs font-bold text-text-primary">{safeNumber(trades)}</div>
        </div>
        <div>
          <div className="text-[9px] text-text-tertiary uppercase font-bold tracking-wider opacity-60 mb-0.5">Win Rate</div>
          <div className="font-mono text-xs font-bold text-accent-success">{safeNumber(winRate)}%</div>
        </div>
        <div>
          <div className="text-[9px] text-text-tertiary uppercase font-bold tracking-wider opacity-60 mb-0.5">Today PnL</div>
          <div className={`font-mono text-xs font-bold ${numericPnl >= 0 ? 'text-accent-success' : 'text-accent-danger'}`}>
            {numericPnl >= 0 ? '+' : ''}${numericPnl.toFixed(2)}
          </div>
        </div>
        <div>
          <div className="text-[9px] text-text-tertiary uppercase font-bold tracking-wider opacity-60 mb-0.5">Avg Hold</div>
          <div className="font-mono text-xs font-bold text-text-primary">{safeScalar(avgHold)}</div>
        </div>
      </div>

      <div className="space-y-1.5 pt-1">
        <div className="flex justify-between text-[9px] uppercase font-bold text-text-tertiary tracking-wider opacity-60">
          <span>Utilization</span>
          <span className="text-text-secondary">{utilization}%</span>
        </div>
        <div className="w-full h-1 bg-bg-tertiary rounded-full overflow-hidden">
          <motion.div 
            initial={{ width: 0 }}
            animate={{ width: `${utilization}%` }}
            transition={{ duration: 1, ease: 'easeOut' }}
            className={`h-full bg-accent-${badgeVariant} rounded-full`}
          ></motion.div>
        </div>
      </div>

      {lastSignal && (
        <div className="mt-auto pt-3 border-t border-border/50 flex items-center justify-between">
          <div className="text-[10px] text-text-tertiary flex items-center gap-2 font-medium">
            Signal: <span className="text-text-secondary font-mono">{safeScalar(lastSignal)}</span>
          </div>
          {signalType && (
            <Badge variant={signalType === 'BUY' ? 'success' : 'danger'} className="text-[8px] px-1 py-0">{signalType}</Badge>
          )}
        </div>
      )}
    </motion.div>
  );
};

export default StrategyCard;
