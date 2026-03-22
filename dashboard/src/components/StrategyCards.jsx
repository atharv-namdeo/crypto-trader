import React from 'react';
import { Target, Activity, Clock, TrendingUp } from 'lucide-react';

const StrategyCards = ({ stats }) => {
  const configs = [
    { title: 'SCALPER', id: 'scalper', hold: '5-15m', desc: 'High-frequency noise capture' },
    { title: 'SWING', id: 'swing', hold: '1-6h', desc: 'Intermediate trend riding' },
    { title: 'POSITION', id: 'position', hold: '4-24h', desc: 'Long-term structural alignment' },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 px-4">
      {configs.map(c => {
        const s = stats[c.id] || { trades: 0, wins: 0, pnl: 0, pos_count: 0, status: 'SCANNING' };
        const winRate = s.trades > 0 ? (s.wins / s.trades * 100).toFixed(1) : '0.0';
        const isProfit = s.pnl >= 0;

        return (
          <div key={c.id} className="card p-5 space-y-4 group transition-all duration-300 hover:border-accent-glow">
            <div className="flex justify-between items-start">
              <div>
                <h3 className="text-lg font-black tracking-tight">{c.title}</h3>
                <p className="text-[10px] text-text-muted font-bold -mt-1">{c.desc}</p>
              </div>
              <span className={`badge ${s.status === 'ACTIVE' ? 'badge-green' : s.status === 'COOLDOWN' ? 'badge-yellow' : 'badge-blue'}`}>
                {s.status}
              </span>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <Metric label="Trades Today" value={s.trades} icon={Target} />
              <Metric label="Win Rate" value={`${winRate}%`} icon={TrendingUp} color={winRate > 50 ? 'text-green' : 'text-red'} />
              <Metric label="Total PnL" value={`$${s.pnl.toFixed(2)}`} icon={Activity} color={isProfit ? 'text-green' : 'text-red'} />
              <Metric label="Hold Time" value={c.hold} icon={Clock} />
            </div>

            <div className="pt-2 border-t border-border flex justify-between items-center text-[10px] uppercase font-black text-text-muted">
              <span>Open Positions: {s.pos_count}</span>
              <span className="text-accent underline cursor-pointer">View Details</span>
            </div>
          </div>
        );
      })}
    </div>
  );
};

const Metric = ({ label, value, icon: Icon, color }) => (
  <div className="flex flex-col">
    <span className="stat-label flex items-center gap-1"><Icon size={10}/> {label}</span>
    <span className={`text-lg font-bold mono mt-0.5 ${color || 'text-text-primary'}`}>{value}</span>
  </div>
);

export default StrategyCards;
