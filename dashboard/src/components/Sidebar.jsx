import React from 'react';
import { LayoutDashboard, Brain, Activity, Briefcase, Settings, Cpu, ShieldCheck } from 'lucide-react';

const Sidebar = ({ activeTab, setTab, botStatus }) => {
  const links = [
    { id: 'dashboard', label: 'Monitor', icon: LayoutDashboard },
    { id: 'live', label: 'Live Trading', icon: ShieldCheck },
    { id: 'trading', label: 'Manual', icon: Activity },
    { id: 'signals', label: 'Intelligence', icon: Brain },
    { id: 'portfolio', label: 'Portfolio', icon: Briefcase },
    { id: 'settings', label: 'Settings', icon: Settings },
  ];

  return (
    <aside className="sidebar hidden md:flex h-full py-6">
      <div className="px-6 mb-10 flex items-center gap-3 group cursor-default">
        <div className="p-2 bg-accent-dim rounded-xl border border-accent/20 group-hover:shadow-glow transition-all">
          <Cpu className="text-accent" size={24} />
        </div>
        <div className="flex flex-col">
          <span className="text-lg font-black tracking-tighter text-text-primary">ANTIGRAVITY</span>
          <span className="text-[9px] font-black text-accent tracking-[.2em] -mt-1 uppercase">Quantum v6.5</span>
        </div>
      </div>

      <nav className="flex-1 space-y-1">
        {links.map(link => (
          <div 
            key={link.id}
            onClick={() => setTab(link.id)}
            className={`sidebar-link ${activeTab === link.id ? 'active' : ''}`}
          >
            <link.icon size={18} strokeWidth={activeTab === link.id ? 2.5 : 1.5} />
            <span className="font-black uppercase tracking-wider">{link.label}</span>
          </div>
        ))}
      </nav>

      <div className="px-4 mt-auto">
         <div className="bg-bg-secondary border border-border rounded-xl p-4 space-y-3">
            <div className="flex items-center justify-between">
               <div className="flex items-center gap-2">
                  <div className={`w-2 h-2 rounded-full ${botStatus === 'ONLINE' ? 'bg-green animate-pulse' : 'bg-red'}`} />
                  <span className="text-[10px] font-black text-text-primary tracking-widest">{botStatus}</span>
               </div>
               <ShieldCheck size={14} className="text-text-muted" />
            </div>
            <div className="progress-bar">
               <div className="progress-fill bg-accent" style={{ width: '88%' }}></div>
            </div>
            <p className="text-[8px] font-bold text-text-muted uppercase text-center opacity-70">
               Engine Load: 12% | Latency: 14ms
            </p>
         </div>
      </div>
    </aside>
  );
};

export default Sidebar;
