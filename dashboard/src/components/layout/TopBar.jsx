import React, { useState, useEffect } from 'react';
import { Bell, Settings, Clock, Activity } from 'lucide-react';
import { useSocket } from '../../context/SocketContext';

const TopBar = () => {
  const [time, setTime] = useState(new Date());
  const { data, connected } = useSocket();

  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  const btc = data?.market?.['BTC/USDT'] || { price: 0, change: 0 };
  const eth = data?.market?.['ETH/USDT'] || { price: 0, change: 0 };

  return (
    <div className="top-bar flex items-center justify-between px-4 fixed top-0 left-0 right-0 z-50 bg-secondary border-b border" style={{ height: '48px' }}>
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <Activity size={20} className="text-accent-primary" />
          <span className="font-bold tracking-tight text-primary">QUANT<span className="text-accent-primary">BOT</span></span>
          <span className="bg-bg-tertiary text-text-secondary text-[10px] px-1.5 py-0.5 rounded border border-border">v7.0</span>
        </div>
      </div>

      <div className="ticker flex items-center gap-6 overflow-hidden max-w-md">
        <div className="ticker-item flex items-center gap-2 font-mono text-sm">
          <span className="text-text-secondary">BTC</span>
          <span className="text-text-primary">${btc.price.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
          <span className={`${btc.change >= 0 ? 'text-accent-success' : 'text-accent-danger'} text-[12px]`}>
            {btc.change >= 0 ? '▲' : '▼'}{Math.abs(btc.change).toFixed(2)}%
          </span>
        </div>
        <div className="ticker-item flex items-center gap-2 font-mono text-sm border-l border-border pl-6">
          <span className="text-text-secondary">ETH</span>
          <span className="text-text-primary">${eth.price.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
          <span className={`${eth.change >= 0 ? 'text-accent-success' : 'text-accent-danger'} text-[12px]`}>
            {eth.change >= 0 ? '▲' : '▼'}{Math.abs(eth.change).toFixed(2)}%
          </span>
        </div>
      </div>

      <div className="flex items-center gap-4 text-text-secondary">
        <div className="flex items-center gap-2 font-mono text-xs border-r border-border pr-4">
          <Clock size={14} />
          {time.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false })}
        </div>
        
        <div className={`flex items-center gap-2 px-2 py-1 rounded border transition-all ${connected ? 'bg-accent-success/10 border-accent-success/20 text-accent-success' : 'bg-accent-danger/10 border-accent-danger/20 text-accent-danger'}`}>
          <div className={`w-2 h-2 rounded-full ${connected ? 'bg-accent-success animate-pulse' : 'bg-accent-danger'}`}></div>
          <span className="text-[11px] font-bold uppercase tracking-wider">{connected ? 'Live' : 'Offline'}</span>
        </div>

        <button className="hover:text-text-primary"><Bell size={18} /></button>
        <button className="hover:text-text-primary"><Settings size={18} /></button>
      </div>
    </div>
  );
};

export default TopBar;
