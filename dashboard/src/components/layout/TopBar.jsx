import React, { useState, useEffect } from 'react';
import { 
  Bell, 
  Settings, 
  Search, 
  Terminal, 
  Zap,
  Clock,
  ChevronDown
} from 'lucide-react';
import { useSocket } from '../../context/SocketContext';
import CountUp from 'react-countup';

const TopBar = () => {
  const { data, connected } = useSocket();
  const [time, setTime] = useState(new Date());

  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  const btcPrice = data?.market?.['BTC/USDT']?.price || 0;
  const btcChange = data?.market?.['BTC/USDT']?.change || 0;
  const ethPrice = data?.market?.['ETH/USDT']?.price || 0;
  const ethChange = data?.market?.['ETH/USDT']?.change || 0;

  return (
    <header className="fixed top-0 left-0 right-0 h-[48px] bg-bg-secondary border-b border-border flex items-center justify-between px-4 z-50">
      {/* Left: Logo */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 bg-accent-primary rounded-sm flex items-center justify-center">
            <Zap size={14} className="text-white fill-current" />
          </div>
          <span className="font-bold text-sm tracking-tighter uppercase whitespace-nowrap">
            Quant<span className="text-accent-primary">Engine</span>
          </span>
        </div>
        <span className="hidden sm:block text-[10px] font-mono bg-bg-tertiary px-1.5 py-0.5 rounded text-text-tertiary border border-border">
          v7.5
        </span>
      </div>

      {/* Center: Live Ticker */}
      <div className="hidden lg:flex items-center gap-8 mx-4 overflow-hidden mask-fade-edges">
        <div className="flex items-center gap-2 min-w-fit">
          <span className="text-[10px] font-bold text-text-tertiary uppercase">BTC/USDT</span>
          <div className="flex items-center gap-1.5">
            <span className="text-[13px] font-mono font-bold text-text-primary">
              $<CountUp end={btcPrice} decimals={2} duration={0.5} preserveValue={true} />
            </span>
            <span className={`text-[10px] font-bold px-1 rounded-sm ${btcChange >= 0 ? 'text-accent-success bg-accent-success/10' : 'text-accent-danger bg-accent-danger/10'}`}>
              {btcChange >= 0 ? '▲' : '▼'} {Math.abs(btcChange).toFixed(1)}%
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2 min-w-fit border-l border-border pl-8">
          <span className="text-[10px] font-bold text-text-tertiary uppercase">ETH/USDT</span>
          <div className="flex items-center gap-1.5">
            <span className="text-[13px] font-mono font-bold text-text-primary">
              $<CountUp end={ethPrice} decimals={2} duration={0.5} preserveValue={true} />
            </span>
            <span className={`text-[10px] font-bold px-1 rounded-sm ${ethChange >= 0 ? 'text-accent-success bg-accent-success/10' : 'text-accent-danger bg-accent-danger/10'}`}>
              {ethChange >= 0 ? '▲' : '▼'} {Math.abs(ethChange).toFixed(1)}%
            </span>
          </div>
        </div>
      </div>

      {/* Right: Actions */}
      <div className="flex items-center gap-4">
        {/* Clock */}
        <div className="hidden md:flex items-center gap-2 text-text-secondary border-r border-border pr-4 h-6">
          <Clock size={14} />
          <span className="text-[11px] font-mono font-bold uppercase tracking-tighter">
            {time.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false })} IST
          </span>
        </div>

        {/* Status Dot */}
        <div className="flex items-center gap-3">
          <div className="relative cursor-pointer text-text-secondary hover:text-text-primary transition-colors">
            <Bell size={18} />
            <div className="absolute -top-0.5 -right-0.5 w-2 h-2 bg-accent-danger rounded-full border border-bg-secondary"></div>
          </div>
          
          <div className="flex items-center gap-2 px-2 py-1 bg-bg-tertiary rounded border border-border cursor-pointer hover:border-border-bright transition-all group">
             <div className={`w-2 h-2 rounded-full ${connected ? 'bg-accent-success' : 'bg-accent-danger'} animate-pulse`}></div>
             <span className="text-[11px] font-bold text-text-secondary group-hover:text-text-primary uppercase tracking-tight">Active</span>
             <ChevronDown size={12} className="text-text-tertiary" />
          </div>
        </div>
      </div>
    </header>
  );
};

export default TopBar;
