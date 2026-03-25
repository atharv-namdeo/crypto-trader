import React, { useState } from 'react';
import { useSocket } from '../../context/SocketContext';
import { motion } from 'framer-motion';
import { 
  ShieldAlert, 
  ShieldCheck, 
  ZapOff, 
  PieChart, 
  AlertTriangle,
  Activity,
  Lock,
  Unlock
} from 'lucide-react';
import Badge from '../ui/Badge';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';

const Risk = () => {
  const { data, connected } = useSocket();
  const [breakers, setBreakers] = useState({
    SCALPER: true,
    SWING: true,
    AI_ENSEMBLE: true
  });

  const portfolio = data?.portfolio || { total_value: 0, drawdown: 0, sharpe: 0 };
  const safeNumber = (val: any) => typeof val === 'number' ? val : parseFloat(String(val || 0)) || 0;
  
  // High-density exposure data
  const exposureData = [
    { asset: 'BTC', exposure: 42, limit: 50, color: '#f59e0b' },
    { asset: 'ETH', exposure: 28, limit: 40, color: '#6366f1' },
    { asset: 'SOL', exposure: 15, limit: 20, color: '#14f195' },
    { asset: 'CASH', exposure: 15, limit: 100, color: '#10b981' }
  ];

  const riskMetrics = [
    { label: 'Value At Risk (VaR)', value: '$412.50', status: 'SAFE', desc: '95% Confidence / 24h' },
    { label: 'Current Drawdown', value: `${safeNumber(portfolio.drawdown).toFixed(2)}%`, status: safeNumber(portfolio.drawdown) > 3 ? 'WARNING' : 'SAFE', desc: 'Max Limit: 5.0%' },
    { label: 'System Volatility', value: '4.2%', status: 'SAFE', desc: 'Historical 30d Avg' },
    { label: 'Leverage Factor', value: '1.2x', status: 'SAFE', desc: 'Target: < 2.0x' }
  ];

  const toggleBreaker = (strategy: string) => {
    setBreakers(prev => ({ ...prev, [strategy]: !prev[strategy as keyof typeof prev] }));
  };

  return (
    <div className="flex flex-col gap-8 pb-20 animate-fade-in">
       {/* HEADER */}
      <header className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-black tracking-tight text-text-primary flex items-center gap-3">
            <ShieldAlert className="text-accent-primary" />
            Risk Management Hub
          </h1>
          <p className="text-sm text-text-tertiary font-medium">Global exposure monitoring and emergency overrides</p>
        </div>
        <Badge variant={connected ? 'success' : 'danger'} className="px-3 py-1 font-black tracking-widest uppercase">
           {connected ? 'Active Guardian' : 'Guardian Offline'}
        </Badge>
      </header>

      {/* RISK SUMMARY GRID */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {riskMetrics.map((m, i) => (
          <div key={i} className="bg-bg-secondary border border-border rounded-xl p-5 shadow-sm group hover:border-border-bright transition-all">
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] font-bold text-text-tertiary uppercase tracking-widest">{m.label}</span>
              {m.status === 'SAFE' ? <ShieldCheck size={14} className="text-accent-success" /> : <AlertTriangle size={14} className="text-accent-warning animate-pulse" />}
            </div>
            <div className="text-xl font-mono font-bold text-text-primary mb-1">{m.value}</div>
            <p className="text-[9px] text-text-tertiary font-medium opacity-60 uppercase tracking-tighter">{m.desc}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* LEFT: EXPOSURE & CONCENTRATION */}
        <section className="lg:col-span-8 bg-bg-secondary border border-border rounded-2xl p-6 shadow-sm flex flex-col h-[500px]">
          <h2 className="text-[11px] font-black text-text-primary uppercase tracking-[0.2em] mb-8 flex items-center gap-2">
            <PieChart size={14} className="text-accent-primary" />
            Asset Exposure & Concentration
          </h2>
          
          <div className="flex-1 w-full min-h-0">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={exposureData} layout="vertical" margin={{ left: 0, right: 40 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e1e3a" horizontal={false} />
                <XAxis type="number" hide domain={[0, 100]} />
                <YAxis 
                  dataKey="asset" 
                  type="category" 
                  axisLine={false} 
                  tickLine={false} 
                  tick={{ fill: '#94a3b8', fontSize: 11, fontWeight: 'bold' }}
                />
                <Tooltip 
                  cursor={{ fill: '#1e1e3a', opacity: 0.4 }}
                  contentStyle={{ background: '#0f0f1a', border: '1px solid #1e1e3a', borderRadius: '8px', fontSize: 11 }}
                />
                <Bar dataKey="exposure" radius={[0, 4, 4, 0]} barSize={24}>
                  {exposureData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="mt-6 grid grid-cols-2 sm:grid-cols-4 gap-4 pt-6 border-t border-border/40">
            {exposureData.map((e, i) => (
              <div key={i} className="flex flex-col gap-1">
                <span className="text-[10px] font-bold text-text-tertiary uppercase tracking-tighter opacity-60">{e.asset} Usage</span>
                <span className="text-xs font-mono font-bold text-text-primary">{e.exposure}% / {e.limit}%</span>
                <div className="h-1 bg-bg-tertiary rounded-full overflow-hidden">
                  <div className="h-full" style={{ width: `${(e.exposure/e.limit)*100}%`, backgroundColor: e.color }}></div>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* RIGHT: CIRCUIT BREAKERS */}
        <aside className="lg:col-span-4 flex flex-col gap-6">
          <section className="bg-bg-secondary border border-border rounded-2xl p-6 shadow-sm flex-1">
            <h2 className="text-[11px] font-black text-text-primary uppercase tracking-[0.2em] mb-8 flex items-center gap-2">
              <ZapOff size={14} className="text-accent-danger" />
              Emergency Circuit Breakers
            </h2>
            
            <div className="space-y-4">
              {Object.entries(breakers).map(([strat, active], i) => (
                <div key={strat} className={`p-4 rounded-xl border transition-all flex flex-col gap-4 ${active ? 'bg-bg-tertiary/20 border-border' : 'bg-accent-danger/5 border-accent-danger/30'}`}>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                       <div className={`w-2 h-2 rounded-full ${active ? 'bg-accent-success animate-pulse' : 'bg-accent-danger'}`}></div>
                       <span className="text-sm font-bold text-text-primary tracking-tight">{strat}</span>
                    </div>
                    <button 
                      onClick={() => toggleBreaker(strat)}
                      className={`p-1.5 rounded-lg border transition-all ${active ? 'bg-bg-tertiary text-text-tertiary hover:text-accent-danger hover:border-accent-danger' : 'bg-accent-danger text-white border-accent-danger shadow-lg'}`}
                    >
                      {active ? <Lock size={16} /> : <Unlock size={16} />}
                    </button>
                  </div>
                  
                  <div className="flex justify-between items-center text-[10px] uppercase font-bold text-text-tertiary">
                    <span>Current Status</span>
                    <span className={active ? 'text-accent-success' : 'text-accent-danger'}>{active ? 'OPERATIONAL' : 'HALTED'}</span>
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-8 p-4 bg-accent-danger/10 border border-accent-danger/20 rounded-xl relative group overflow-hidden">
               <div className="absolute inset-0 bg-accent-danger opacity-0 group-hover:opacity-5 transition-opacity"></div>
               <div className="flex flex-col gap-2 relative z-10">
                 <div className="flex items-center gap-2 text-accent-danger">
                   <AlertTriangle size={14} />
                   <span className="text-[10px] font-black uppercase tracking-[0.1em]">Nuclear Option</span>
                 </div>
                 <button className="w-full py-2 bg-accent-danger text-white text-xs font-black uppercase tracking-widest rounded-lg shadow-[0_4px_12px_rgba(239,68,68,0.3)] hover:scale-[1.02] active:scale-95 transition-all">
                    FORCE KILL ALL SYSTEMS
                 </button>
               </div>
            </div>
          </section>
        </aside>

      </div>
    </div>
  );
};

export default Risk;
