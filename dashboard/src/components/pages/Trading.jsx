import React, { useState, useEffect } from 'react';
import CandlestickChart from '../charts/CandlestickChart';
import PositionsTable from '../tables/PositionsTable';
import TradeHistory from '../tables/TradeHistory';
import { useSocket } from '../../context/SocketContext';

const Trading = () => {
  const { data, connected } = useSocket();
  const [activeTab, setActiveTab] = useState('positions');

  const positions = (data?.positions || []).map(p => ({
    strategy: p.strategy?.toUpperCase() || 'UNKNOWN',
    symbol: p.symbol,
    side: p.side === 'BUY' ? 'LONG' : 'SHORT',
    entry: p.entry,
    current: p.current,
    pnlUsd: p.pnl,
    pnlPct: p.pnl_pct,
    duration: p.duration || '--'
  }));

  // Trade history isn't directly in 'engine_update' data for all historical trades,
  // but let's assume 'trade_history' is synced or we fetch it.
  // For now, I'll use the 'signals' as proxy or mock history if trade_history is missing.
  const history = data?.trade_history || []; 

  return (
    <div className="flex flex-col gap-6 animate-fade-in">
      <div className="card p-4 min-h-[60vh]">
        <CandlestickChart data={data.latest_candles || []} symbol="BTC/USDT" timeframe="1m" />
      </div>

      <div className="card overflow-hidden">
        <div className="flex border-b border-border bg-bg-secondary">
          <button 
            onClick={() => setActiveTab('positions')}
            className={`px-6 py-3 text-[11px] font-bold uppercase tracking-widest border-b-2 transition-all ${activeTab === 'positions' ? 'border-accent-primary text-accent-primary bg-accent-primary/5' : 'border-transparent text-text-tertiary hover:text-text-secondary hover:bg-bg-hover'}`}
          >
            Open Positions ({positions.length})
          </button>
          <button 
            onClick={() => setActiveTab('history')}
            className={`px-6 py-3 text-[11px] font-bold uppercase tracking-widest border-b-2 transition-all ${activeTab === 'history' ? 'border-accent-primary text-accent-primary bg-accent-primary/5' : 'border-transparent text-text-tertiary hover:text-text-secondary hover:bg-bg-hover'}`}
          >
            Trade History
          </button>
          <button 
            onClick={() => setActiveTab('orders')}
            className={`px-6 py-3 text-[11px] font-bold uppercase tracking-widest border-b-2 transition-all ${activeTab === 'orders' ? 'border-accent-primary text-accent-primary bg-accent-primary/5' : 'border-transparent text-text-tertiary hover:text-text-secondary hover:bg-bg-hover'}`}
          >
            Active Orders
          </button>
        </div>

        <div className="p-4 bg-bg-primary">
          {activeTab === 'positions' && <PositionsTable positions={positions} />}
          {activeTab === 'history' && <TradeHistory trades={history} />}
          {activeTab === 'orders' && <div className="py-12 text-center text-text-tertiary italic">No active orders detected.</div>}
        </div>
      </div>
    </div>
  );
};

export default Trading;
