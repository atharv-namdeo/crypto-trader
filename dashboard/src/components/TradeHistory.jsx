import React from 'react';
import { History, Download, ChevronLeft, ChevronRight } from 'lucide-react';

const TradeHistory = ({ trades }) => {
  return (
    <div className="card overflow-hidden">
      <div className="px-6 py-4 border-b border-border flex justify-between items-center bg-bg-secondary">
        <div className="flex items-center gap-2">
          <History size={16} className="text-accent" />
          <h3 className="text-xs font-black uppercase tracking-widest text-[#7a8ba5]">Performance History</h3>
        </div>
        <button className="btn-ghost flex items-center gap-2 text-[10px] font-black uppercase">
          <Download size={14} />
          Export CSV
        </button>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr>
              <th className="table-header">Date / Time</th>
              <th className="table-header">Pair / Engine</th>
              <th className="table-header text-center">Outcome</th>
              <th className="table-header">Profit/Loss</th>
              <th className="table-header">Reason</th>
            </tr>
          </thead>
          <tbody className="mono text-[11px]">
            {trades.length === 0 ? (
              <tr>
                <td colSpan="5" className="py-12 text-center text-text-muted italic">
                  No historical trades found. The bot is actively scanning...
                </td>
              </tr>
            ) : (
              trades.slice(0, 10).map((t, idx) => {
                const isWin = t.pnl > 0;
                return (
                  <tr key={idx} className="table-row">
                    <td className="table-cell text-text-secondary opacity-70 italic">{t.time}</td>
                    <td className="table-cell">
                      <div className="flex flex-col">
                        <span className="font-black text-text-primary uppercase tracking-tighter">{t.symbol}</span>
                        <span className="text-[9px] text-text-muted font-bold opacity-60">[{t.strategy}]</span>
                      </div>
                    </td>
                    <td className="table-cell text-center">
                      <span className={`px-2 py-0.5 rounded text-[9px] font-black uppercase ${isWin ? 'bg-green-dim text-green' : 'bg-red-dim text-red'}`}>
                        {isWin ? 'WIN' : 'LOSS'}
                      </span>
                    </td>
                    <td className={`table-cell font-black ${isWin ? 'text-green' : 'text-red'}`}>
                      {isWin ? '+' : ''}${t.pnl.toFixed(2)}
                    </td>
                    <td className="table-cell text-text-muted font-bold tracking-tight opacity-50">{t.reason}</td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      <div className="px-6 py-3 border-t border-border flex justify-between items-center bg-bg-secondary text-[10px] font-black uppercase text-text-muted">
         <span>Showing 1-10 of {trades.length} trades</span>
         <div className="flex gap-2">
            <button className="p-1 hover:text-accent disabled:opacity-20"><ChevronLeft size={16}/></button>
            <button className="p-1 hover:text-accent disabled:opacity-20"><ChevronRight size={16}/></button>
         </div>
      </div>
    </div>
  );
};

export default TradeHistory;
