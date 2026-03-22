import React from 'react';
import { XCircle, ArrowUpRight, ArrowDownRight, MoreHorizontal } from 'lucide-react';

const OpenPositions = ({ positions, onAction }) => {
  return (
    <div className="card overflow-hidden">
      <div className="px-6 py-4 border-b border-border flex justify-between items-center">
        <h3 className="text-sm font-black uppercase tracking-widest text-[#7a8ba5]">Live Open Positions</h3>
        <span className="badge badge-blue">{positions.length} ACTIVE</span>
      </div>
      
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr>
              <th className="table-header">Symbol / Strategy</th>
              <th className="table-header">Side</th>
              <th className="table-header">Size / Entry</th>
              <th className="table-header">PnL</th>
              <th className="table-header text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {positions.length === 0 ? (
              <tr>
                <td colSpan="5" className="py-12 text-center text-text-muted text-sm font-medium">
                  No active trades. Scanning for high-probability signals...
                </td>
              </tr>
            ) : (
              positions.map((p, idx) => (
                <tr key={idx} className="table-row group">
                  <td className="table-cell">
                    <div className="flex flex-col">
                      <span className="font-black text-sm">{p.symbol}</span>
                      <span className="text-[10px] text-text-muted font-bold uppercase">{p.strategy}</span>
                    </div>
                  </td>
                  <td className="table-cell">
                    <span className={`badge ${p.side === 'LONG' ? 'badge-green' : 'badge-red'}`}>
                      {p.side}
                    </span>
                  </td>
                  <td className="table-cell">
                    <div className="flex flex-col">
                      <span className="mono text-xs">{p.qty.toFixed(4)}</span>
                      <span className="text-[10px] text-text-muted font-medium">${p.entry.toLocaleString()}</span>
                    </div>
                  </td>
                  <td className="table-cell">
                    <div className="flex items-center gap-1.5 font-black mono text-sm">
                      {p.pnl >= 0 ? <ArrowUpRight size={14} className="text-green"/> : <ArrowDownRight size={14} className="text-red"/>}
                      <span className={p.pnl >= 0 ? 'text-green' : 'text-red'}>
                        ${p.pnl.toFixed(2)}
                      </span>
                    </div>
                  </td>
                  <td className="table-cell text-right">
                    <div className="flex justify-end gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                      <button 
                        onClick={() => onAction('move_stop', p)}
                        className="btn-ghost p-1.5" title="Move Stop to Breakeven"
                      >
                        <MoreHorizontal size={16} />
                      </button>
                      <button 
                        onClick={() => onAction('close', p)}
                        className="btn-danger p-1.5 flex items-center gap-1"
                      >
                        <XCircle size={14} />
                        CLOSE
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default OpenPositions;
