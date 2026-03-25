import React, { useState, useEffect } from 'react';
import { 
  Bell, 
  Settings, 
  Zap,
  Clock,
  ShieldAlert,
  Activity,
  PieChart
} from 'lucide-react';
import { useSocket } from '../../context/SocketContext';

const TopBar = () => {
  const { data, connected } = useSocket();
  const safeNumber = (val: any) => typeof val === 'number' ? val : parseFloat(String(val || 0)) || 0;
  const safeScalar = (val: any) => (typeof val === 'string' || typeof val === 'number') ? val : '';
  
  const [time, setTime] = useState(new Date());

  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  const portfolioValue = safeNumber(data?.portfolio?.total_value || 12450.32);
  const portfolioChange = safeNumber(data?.portfolio?.daily_change_pct || 2.5);
  const dailyPnl = safeNumber(data?.portfolio?.daily_pnl || 312.45);

  return (
    <header className="fixed top-0 left-0 right-0 h-[56px] bg-bg-secondary border-b border-border flex items-center justify-between px-4 z-50 shadow-sm backdrop-blur-md bg-opacity-80">
      <div className="flex items-center gap-6">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 bg-accent-primary rounded flex items-center justify-center shadow-lg shadow-accent-primary/20">
            <Zap size={16} className="text-white fill-current" />
          </div>
          <div className="flex flex-col">
            <span className="font-bold text-sm tracking-tighter uppercase leading-none">
              Quant<span className="text-accent-primary">Engine</span>
            </span>
            <span className="text-[9px] font-mono text-text-tertiary flex items-center gap-1">
              <ShieldAlert size={8} /> Production v8.0-Stable
            </span>
          </div>
        </div>

        <div className="hidden xl:flex items-center gap-2 px-3 py-1.5 bg-bg-tertiary rounded-full border border-border group cursor-pointer hover:border-accent-success/50 transition-all">
          <div className="relative">
            <div className={`w-2 h-2 rounded-full ${connected ? 'bg-accent-success' : 'bg-accent-danger'} shadow-[0_0_8px] ${connected ? 'shadow-accent-success/50' : 'shadow-accent-danger/50'}`}></div>
            {connected && <div className="absolute inset-0 bg-accent-success rounded-full animate-ping opacity-40"></div>}
          </div>
          <span className="text-[10px] font-bold text-text-secondary uppercase tracking-widest">
            {connected ? 'Standard Operation' : 'System Offline'}
          </span>
          <div className="h-3 w-px bg-border mx-1"></div>
          <span className="text-[9px] font-mono text-accent-success">Bybit Demo</span>
        </div>
      </div>

      <div className="hidden lg:flex items-center gap-10">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-bg-tertiary rounded-lg border border-border">
            <PieChart size={16} className="text-text-tertiary" />
          </div>
          <div className="flex flex-col">
            <span className="text-[10px] font-bold text-text-tertiary uppercase tracking-tight">Portfolio Value</span>
            <div className="flex items-baseline gap-2">
              <span className="text-lg font-mono font-bold text-text-primary tracking-tighter">
                ${portfolioValue.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </span>
              <span className={`text-[11px] font-bold ${portfolioChange >= 0 ? 'text-accent-success' : 'text-accent-danger'}`}>
                {portfolioChange >= 0 ? '+' : ''}{portfolioChange.toFixed(2)}%
              </span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-8 border-l border-border pl-8">
          <div className="flex flex-col">
            <span className="text-[9px] font-bold text-text-tertiary uppercase">Daily Net P&L</span>
            <span className={`text-sm font-mono font-bold ${dailyPnl >= 0 ? 'text-accent-success' : 'text-accent-danger'}`}>
              {dailyPnl >= 0 ? '+' : '-'}${Math.abs(dailyPnl).toFixed(2)}
            </span>
          </div>
          <div className="flex flex-col text-right">
             <span className="text-[9px] font-bold text-text-tertiary uppercase">Bot Status</span>
             <span className="text-[10px] font-black text-text-primary uppercase tracking-widest">
                {safeScalar(data?.status) || 'Active'}
             </span>
          </div>
        </div>
      </div>

      <div className="flex items-center gap-5">
        <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 bg-accent-success/5 rounded border border-accent-success/20">
          <Activity size={12} className="text-accent-success animate-pulse" />
          <span className="text-[10px] font-bold text-accent-success uppercase">Health 99%</span>
        </div>

        <div className="hidden md:flex flex-col items-end border-r border-border pr-5">
          <div className="flex items-center gap-1.5 text-text-primary">
            <Clock size={12} className="text-text-tertiary" />
            <span className="text-[12px] font-mono font-bold tracking-tighter">
              {time.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false })}
            </span>
          </div>
          <span className="text-[8px] font-bold text-text-tertiary uppercase tracking-normal">Asia/Kolkata (IST)</span>
        </div>

        <div className="flex items-center gap-3">
          <button className="p-2 hover:bg-bg-tertiary rounded-full transition-colors relative">
            <Bell size={20} className="text-text-secondary" />
            <span className="absolute top-2 right-2 w-2 h-2 bg-accent-danger rounded-full border-2 border-bg-secondary"></span>
          </button>
          <button className="p-2 hover:bg-bg-tertiary rounded-full transition-colors">
            <Settings size={20} className="text-text-secondary" />
          </button>
          <div className="w-8 h-8 rounded-full bg-accent-primary flex items-center justify-center text-white text-xs font-bold cursor-pointer border border-accent-primary-bright">
            AN
          </div>
        </div>
      </div>
    </header>
  );
};

export default TopBar;
