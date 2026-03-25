import React from 'react';
import Badge from '../ui/Badge';
import { motion } from 'framer-motion';

interface SignalCardProps {
  strategy: string;
  symbol: string;
  side: 'BUY' | 'SELL' | 'HOLD';
  score: number;
  confidence: number;
  time: string;
}

const SignalCard: React.FC<SignalCardProps> = ({ strategy, symbol, side, score, confidence, time }) => {
  const strategyVariants: Record<string, any> = {
    SCALPER: 'cyan',
    SWING: 'purple',
    POSITION: 'orange',
    AI_ENSEMBLE: 'primary',
  };

  const sideVariants: Record<string, any> = {
    BUY: 'success',
    SELL: 'danger',
    HOLD: 'default',
  };

  return (
    <motion.div 
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      className="signal-card p-3 rounded-xl bg-bg-secondary border border-border hover:border-accent-primary/30 transition-all duration-300 mb-2 group shadow-sm hover:shadow-[0_0_15px_rgba(var(--accent-primary-rgb),0.05)]"
    >
      <div className="flex items-center justify-between mb-2.5">
        <div className="flex items-center gap-2">
          <Badge variant={strategyVariants[strategy] || 'default'} className="text-[9px] px-1.5 py-0.5">{strategy}</Badge>
          <span className="font-mono font-bold text-text-primary text-[13px]">{symbol}</span>
        </div>
        <Badge variant={sideVariants[side] || 'default'} className="text-[10px] font-black">{side}</Badge>
      </div>

      <div className="grid grid-cols-2 gap-3 mb-2">
        <div className="flex flex-col">
          <span className="text-[9px] text-text-tertiary font-bold tracking-wider uppercase opacity-60">Score</span>
          <span className="text-xs font-mono font-bold text-text-secondary">{(score || 0).toFixed(4)}</span>
        </div>
        <div className="flex flex-col">
          <span className="text-[9px] text-text-tertiary font-bold tracking-wider uppercase opacity-60">Confidence</span>
          <span className={`text-xs font-mono font-bold ${confidence > 0.8 ? 'text-accent-success' : 'text-text-secondary'}`}>{(confidence * 100).toFixed(1)}%</span>
        </div>
      </div>

      <div className="flex items-center justify-between text-[10px] pt-1.5 border-t border-border/50">
        <span className="text-text-tertiary font-medium">Decided at</span>
        <span className="text-text-tertiary font-mono">{time}</span>
      </div>
    </motion.div>
  );
};

export default SignalCard;
