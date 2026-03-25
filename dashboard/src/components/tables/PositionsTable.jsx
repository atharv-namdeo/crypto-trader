import React from 'react';
import Badge from '../ui/Badge';

const PositionsTable = ({ positions = [] }) => {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left border-collapse">
        <thead>
          <tr className="border-b border-border">
            <th className="py-3 px-4 text-[10px] font-bold text-text-tertiary uppercase tracking-widest">Strategy</th>
            <th className="py-3 px-4 text-[10px] font-bold text-text-tertiary uppercase tracking-widest">Symbol</th>
            <th className="py-3 px-4 text-[10px] font-bold text-text-tertiary uppercase tracking-widest">Side</th>
            <th className="py-3 px-4 text-[10px] font-bold text-text-tertiary uppercase tracking-widest">Entry</th>
            <th className="py-3 px-4 text-[10px] font-bold text-text-tertiary uppercase tracking-widest">Current</th>
            <th className="py-3 px-4 text-[10px] font-bold text-text-tertiary uppercase tracking-widest">PnL ($)</th>
            <th className="py-3 px-4 text-[10px] font-bold text-text-tertiary uppercase tracking-widest">PnL (%)</th>
            <th className="py-3 px-4 text-[10px] font-bold text-text-tertiary uppercase tracking-widest">Duration</th>
            <th className="py-3 px-4 text-[10px] font-bold text-text-tertiary uppercase tracking-widest">Actions</th>
          </tr>
        </thead>
        <tbody>
          {positions.length > 0 ? positions.map((pos, idx) => (
            <tr key={idx} className="border-b border-border/50 hover:bg-bg-hover transition-colors group">
              <td className="py-3 px-4"><Badge variant={pos.strategy === 'SCALPER' ? 'cyan' : 'purple'}>{pos.strategy}</Badge></td>
              <td className="py-3 px-4 font-mono font-bold text-text-primary">{pos.symbol}</td>
              <td className="py-3 px-4"><Badge variant={pos.side === 'LONG' ? 'success' : 'danger'}>{pos.side}</Badge></td>
              <td className="py-3 px-4 font-mono text-text-secondary">${pos.entry.toFixed(2)}</td>
              <td className="py-3 px-4 font-mono text-text-primary">${pos.current.toFixed(2)}</td>
              <td className={`py-3 px-4 font-mono font-bold ${pos.pnlUsd >= 0 ? 'text-accent-success' : 'text-accent-danger'}`}>
                {pos.pnlUsd >= 0 ? '+' : ''}{pos.pnlUsd.toFixed(2)}
              </td>
              <td className={`py-3 px-4 font-mono font-bold ${pos.pnlPct >= 0 ? 'text-accent-success' : 'text-accent-danger'}`}>
                {pos.pnlPct >= 0 ? '+' : ''}{pos.pnlPct.toFixed(2)}%
              </td>
              <td className="py-3 px-4 text-text-tertiary text-xs">{pos.duration}</td>
              <td className="py-3 px-4">
                <button className="px-3 py-1 rounded bg-accent-danger/10 text-accent-danger border border-accent-danger/20 text-[10px] font-bold hover:bg-accent-danger hover:text-white transition-all">CLOSE</button>
              </td>
            </tr>
          )) : (
            <tr>
              <td colSpan="9" className="py-12 text-center text-text-tertiary italic">No open positions detected.</td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
};

export default PositionsTable;
