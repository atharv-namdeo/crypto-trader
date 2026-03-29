import React from 'react';
import Badge from '../ui/Badge';

const TradeHistory = ({ trades = [] }) => {
  return (
    <div className="flex flex-col gap-4">
      {/* Filters Bar */}
      <div className="flex items-center justify-between gap-4 p-2 bg-bg-tertiary rounded-card border border-border">
          <div className="flex gap-2">
            <select className="bg-bg-primary border-border text-[11px] font-bold uppercase py-1 px-3 rounded">
                <option>All Strategies</option>
                <option>Scalper</option>
                <option>Swing</option>
                <option>Position</option>
            </select>
            <select className="bg-bg-primary border-border text-[11px] font-bold uppercase py-1 px-3 rounded">
                <option>All Symbols</option>
                <option>BTC/USDT</option>
                <option>ETH/USDT</option>
            </select>
          </div>
          <button 
            onClick={() => window.open('/api/v1/export/trades', '_blank')}
            className="px-4 py-1 bg-bg-primary border border-border rounded text-[11px] font-bold text-text-secondary hover:text-text-primary hover:border-border-bright"
          >
            Export CSV
          </button>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
            <thead>
            <tr className="border-b border-border">
                <th className="py-3 px-4 text-[10px] font-bold text-text-tertiary uppercase tracking-widest">Time</th>
                <th className="py-3 px-4 text-[10px] font-bold text-text-tertiary uppercase tracking-widest">Strategy</th>
                <th className="py-3 px-4 text-[10px] font-bold text-text-tertiary uppercase tracking-widest">Symbol</th>
                <th className="py-3 px-4 text-[10px] font-bold text-text-tertiary uppercase tracking-widest">Side</th>
                <th className="py-3 px-4 text-[10px] font-bold text-text-tertiary uppercase tracking-widest">Entry</th>
                <th className="py-3 px-4 text-[10px] font-bold text-text-tertiary uppercase tracking-widest">Exit</th>
                <th className="py-3 px-4 text-[10px] font-bold text-text-tertiary uppercase tracking-widest">PnL ($)</th>
                <th className="py-3 px-4 text-[10px] font-bold text-text-tertiary uppercase tracking-widest">PnL (%)</th>
                <th className="py-3 px-4 text-[10px] font-bold text-text-tertiary uppercase tracking-widest">Duration</th>
                <th className="py-3 px-4 text-[10px] font-bold text-text-tertiary uppercase tracking-widest">Reason</th>
            </tr>
            </thead>
            <tbody>
            {trades.length > 0 ? trades.map((trade, idx) => (
                <tr key={idx} className="border-b border-border/50 hover:bg-bg-hover transition-colors">
                <td className="py-3 px-4 text-xs text-text-tertiary font-mono">{trade.time}</td>
                <td className="py-3 px-4"><Badge variant={trade.strategy === 'SCALPER' ? 'cyan' : 'purple'}>{trade.strategy}</Badge></td>
                <td className="py-3 px-4 font-mono font-bold text-text-primary">{trade.symbol}</td>
                <td className="py-3 px-4"><Badge variant={trade.side === 'LONG' ? 'success' : 'danger'}>{trade.side}</Badge></td>
                <td className="py-3 px-4 font-mono text-text-secondary">${trade.entry.toFixed(2)}</td>
                <td className="py-3 px-4 font-mono text-text-primary">${trade.exit.toFixed(2)}</td>
                <td className={`py-3 px-4 font-mono font-bold ${trade.pnlUsd >= 0 ? 'text-accent-success' : 'text-accent-danger'}`}>
                    {trade.pnlUsd >= 0 ? '+' : ''}{trade.pnlUsd.toFixed(2)}
                </td>
                <td className={`py-3 px-4 font-mono font-bold ${trade.pnlPct >= 0 ? 'text-accent-success' : 'text-accent-danger'}`}>
                    {trade.pnlPct >= 0 ? '+' : ''}{trade.pnlPct.toFixed(2)}%
                </td>
                <td className="py-3 px-4 text-text-tertiary text-xs">{trade.duration}</td>
                <td className="py-3 px-4"><Badge variant="default">{trade.reason}</Badge></td>
                </tr>
            )) : (
                <tr>
                <td colSpan="10" className="py-12 text-center text-text-tertiary italic">No trade history available.</td>
                </tr>
            )}
            </tbody>
        </table>
      </div>
      
      {/* Pagination Placeholder */}
      <div className="flex justify-center gap-2 mt-4">
          <button className="px-3 py-1 bg-bg-tertiary border border-border rounded text-[10px] font-bold text-text-tertiary">Prev</button>
          <button className="px-3 py-1 bg-accent-primary text-white border border-accent-primary rounded text-[10px] font-bold">1</button>
          <button className="px-3 py-1 bg-bg-tertiary border border-border rounded text-[10px] font-bold text-text-secondary">2</button>
          <button className="px-3 py-1 bg-bg-tertiary border border-border rounded text-[10px] font-bold text-text-secondary">Next</button>
      </div>
    </div>
  );
};

export default TradeHistory;
