import React from 'react';
import { ArrowUpRight, ArrowDownRight, XCircle } from 'lucide-react';

const PositionsTable = ({ positions = [] }) => {
  return (
    <table className="w-full text-left border-collapse">
      <thead className="sticky top-0 bg-bg-secondary z-10 shadow-sm">
        <tr className="border-b border-border">
          <th className="px-6 py-3 text-[10px] font-bold text-text-tertiary uppercase tracking-widest">Symbol/Strategy</th>
          <th className="px-4 py-3 text-[10px] font-bold text-text-tertiary uppercase tracking-widest">Side</th>
          <th className="px-4 py-3 text-[10px] font-bold text-text-tertiary uppercase tracking-widest">Size/Entry</th>
          <th className="px-4 py-3 text-[10px] font-bold text-text-tertiary uppercase tracking-widest">Mark Price</th>
          <th className="px-4 py-3 text-[10px] font-bold text-text-tertiary uppercase tracking-widest">PnL (Unrealized)</th>
          <th className="px-6 py-3 text-[10px] font-bold text-text-tertiary uppercase tracking-widest text-right">Actions</th>
        </tr>
      </thead>
      <tbody>
        {positions.length > 0 ? positions.map((p, i) => (
          <tr key={i} className="border-b border-border/50 hover:bg-bg-hover transition-colors group">
            <td className="px-6 py-4">
              <div className="flex flex-col">
                <span className="text-[13px] font-bold text-text-primary">{p.symbol}</span>
                <span className="text-[10px] font-bold text-text-tertiary uppercase">{p.strategy}</span>
              </div>
            </td>
            <td className="px-4 py-4">
              <span className={`px-2 py-0.5 rounded-[2px] text-[10px] font-bold border ${
                p.side === 'LONG' 
                ? 'text-accent-success bg-accent-success/10 border-accent-success/20' 
                : 'text-accent-danger bg-accent-danger/10 border-accent-danger/20'
              }`}>
                {p.side}
              </span>
            </td>
            <td className="px-4 py-4">
              <div className="flex flex-col">
                <span className="text-[12px] font-mono font-medium">{(p.qty || 0).toFixed(4)}</span>
                <span className="text-[10px] text-text-tertiary font-mono">${(p.entry || 0).toLocaleString()}</span>
              </div>
            </td>
            <td className="px-4 py-4">
              <span className="text-[12px] font-mono text-text-secondary">${(p.mark || p.entry || 0).toLocaleString()}</span>
            </td>
            <td className="px-4 py-4">
              <div className={`flex items-center gap-1.5 text-[13px] font-mono font-bold ${(p.pnl || 0) >= 0 ? 'text-accent-success' : 'text-accent-danger'}`}>
                {(p.pnl || 0) >= 0 ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}
                ${(p.pnl || 0).toFixed(2)}
                <span className="text-[10px] opacity-70">({(p.entry && p.qty ? ((p.pnl || 0) / (p.entry * p.qty) * 100) : 0).toFixed(2)}%)</span>
              </div>
            </td>
            <td className="px-6 py-4 text-right">
               <div className="flex justify-end gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                 <button className="p-1 px-2 border border-border rounded-[2px] text-[10px] font-bold uppercase hover:bg-bg-tertiary">TP/SL</button>
                 <button className="flex items-center gap-1 px-2 py-1 bg-accent-danger text-white text-[10px] font-bold rounded-[2px] hover:opacity-90">
                   <XCircle size={12} />
                   CLOSE
                 </button>
               </div>
            </td>
          </tr>
        )) : (
          <tr>
            <td colSpan="6" className="py-16 text-center text-text-tertiary text-xs italic">No active positions. The engine is currently scanning for opportunities.</td>
          </tr>
        )}
      </tbody>
    </table>
  );
};

export default PositionsTable;
