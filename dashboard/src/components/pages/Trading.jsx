import React, { useState } from 'react';
import CandlestickChart from '../charts/CandlestickChart';
import { useSocket } from '../../context/SocketContext';
import PositionsTable from '../tables/PositionsTable';
import TradeHistory from '../tables/TradeHistory';
import { 
  ArrowUpRight, 
  ArrowDownRight, 
  XCircle, 
  MoreHorizontal,
  History,
  Briefcase,
  ListFilter
} from 'lucide-react';

const Trading = () => {
  const { data, connected } = useSocket();
  const [activeTab, setActiveTab] = useState('positions');

  const positions = data?.positions || [];
  const orders = data?.orders || [];
  const trades = data?.trades || [];

  return (
    <div className="flex flex-col gap-4 animate-fade-in h-full">
      {/* Upper Section: Main Terminal Chart */}
      <div className="card p-4 min-h-[500px] flex flex-col">
        <CandlestickChart data={data?.latest_candles || []} symbol="BTC/USDT" />
      </div>

      {/* Lower Section: Data Tables */}
      <div className="card flex-1 min-h-[400px] flex flex-col overflow-hidden">
        {/* Table Tabs */}
        <div className="flex items-center justify-between border-b border-border px-4 bg-bg-tertiary/30">
          <div className="flex">
            {[
              { id: 'positions', label: 'Open Positions', icon: Briefcase, count: positions.length },
              { id: 'orders', label: 'Active Orders', icon: ListFilter, count: orders.length },
              { id: 'history', label: 'Trade History', icon: History, count: trades.length },
            ].map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-6 py-3 text-[11px] font-bold uppercase tracking-wider transition-all border-b-2 ${
                  activeTab === tab.id 
                  ? 'border-accent-primary text-accent-primary bg-accent-primary/5' 
                  : 'border-transparent text-text-tertiary hover:text-text-secondary'
                }`}
              >
                <tab.icon size={14} />
                {tab.label}
                {tab.count > 0 && (
                  <span className={`ml-1 px-1.5 py-0.5 rounded-full text-[9px] ${activeTab === tab.id ? 'bg-accent-primary text-white' : 'bg-bg-tertiary text-text-tertiary'}`}>
                    {tab.count}
                  </span>
                )}
              </button>
            ))}
          </div>
        </div>

        {/* Table Content */}
        <div className="flex-1 overflow-auto no-scrollbar">
          {activeTab === 'positions' && (
            <PositionsTable positions={positions} />
          )}

          {activeTab === 'orders' && (
             <div className="flex flex-col items-center justify-center py-20 text-text-tertiary">
                <ListFilter size={32} className="mb-4 opacity-20" />
                <p className="text-sm font-bold uppercase tracking-widest">No Active Orders</p>
                <p className="text-[11px] opacity-60">Buy/Sell limit orders will appear here when placed by strategies.</p>
             </div>
          )}

          {activeTab === 'history' && (
            <TradeHistory trades={trades} />
          )}
        </div>
      </div>
    </div>
  );
};

export default Trading;
